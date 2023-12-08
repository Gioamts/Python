import os
os.add_dll_directory('C:\Program Files (x86)\Keysight\IO Libraries Suite\\bin')
import pyvisa as visa
from time import sleep

class LCR:
  
    def __init__(self, gpib_address='GPIB0::18::INSTR', freq=400, ACLevel=0.04, Int="MED", Ave=4, Assoc="CSRS"):

        self.freq = freq
        self.ACLevel = ACLevel
        self.Int = Int
        self.Ave = Ave
        self.Assoc = Assoc
        self.gpib_address = gpib_address

        self.rm = visa.ResourceManager()
        self.LCR = self.rm.open_resource(self.gpib_address)
        self.LCR.timeout = None
        self.LCR.write('BIAS:VOLT 0V')
        self.LCR.write('''BIAS:STAT OFF''')

    def Configure(self):

        self.LCR.write('TRIG:SOUR BUS')
        self.LCR.write('INIT:CONT ON')
        self.LCR.write(f'APER {self.Int},{self.Ave}')
        self.LCR.write(f'FUNC:IMP {self.Assoc}')
        self.LCR.write(f'VOLT {self.ACLevel}V')
        self.LCR.write(f'FREQ {self.freq}KHZ')

    def release(self):

        self.LCR.write('BIAS:VOLT 0V')
        self.LCR.write('BIAS:STAT ON')
        sleep(0.05)
        self.LCR.write('''BIAS:STAT OFF''')
        self.LCR.write('''TRIG:SOURCE INT''')
    
    def wait(self,Int_time, Freq, Nb_aver):
        if Int_time=="SHOR":
            A=0.05
            if Freq<1:
                A=0.3
            if Freq<0.1:
                A=1.8
        if Int_time=="MED":
            A=0.15
            if Freq<1:
                A=0.4
            if Freq<0.1:
                A=1.8
        if Int_time=="LONG":
            A=0.8
            if Freq<1:
                A=1.0
            if Freq<0.1:
                A=2.0
        A=A*Nb_aver
        return(A)
    
    def Alim4284(self):

        self.LCR.write('''BIAS:VOLT 0V''')
        self.LCR.write('''BIAS:STAT ON''')
        sleep(0.05)

    def Measure_RC(self):
        self.LCR.write('TRIGGER')
        sleep(self.wait(self.Int, self.freq, self.Ave))
        CR = self.LCR.query('FETC?')
        C = ([tuple(float(k) for k in CR.split(","))][0][0])
        Rgate = ([tuple(float(k) for k in CR.split(","))][0][1])

        return((C, Rgate))

class Analyzer:

    def __init__(self, gpib_address='GPIB0::18::INSTR', Int=2, Ave=4, Vd=0.025, Vs=0, Vb=0, Vg_start=0, Vg_stop=1, step=100):

        self.Int = Int
        self.Ave = Ave
        self.Vds = Vd - Vs
        self.Vs = Vs
        self.Vb = Vb
        self.Vgsstart = Vg_start - Vs  #Correction in respect to Vs
        self.Vgsstop = Vg_stop - Vs  #Correction in respect to Vs
        self.Nbsteps = (abs(self.Vgstop - self.Vgstart) // step) + 1

        rm = visa.ResourceManager()
        self.Ana = rm.open_resource(gpib_address)
        self.Ana.timeout = None
        self.reset_Analyzer()

    def reset_Analyzer(self):

        self.Ana.write("*RST")

    def Define_SMU(self, SMU_Drain=1, SMU_Source=2, SMU_Gate=3, SMU_Substrate=4):

        self.SMU_Drain = SMU_Drain
        self.SMU_Source = SMU_Source
        self.SMU_Gate = SMU_Gate
        self.SMU_Substrate = SMU_Substrate
    
    def Enable_Channels(self):

        self.Ana.write("US")
        self.Ana.write("BC")
        self.Ana.write("CN")

    def configure_measurement(self):

        self.Ana.write(f"SLI {self.Int}")
        self.Ana.write(f"AV {self.Ave}")
        self.Ana.write("WM 1")    #No stop at compliance
        self.Ana.write("FMT 2,1") #Output data is set to ASCII format
        self.Ana.write(f"MM 1,{self.SMU_Gate},{self.SMU_Drain},{self.SMU_Source},{self.SMU_Substrate}")
        self.Ana.write(f"CMM {self.SMU_Gate},1")
        self.Ana.write(f"CMM {self.SMU_Drain},1")
        self.Ana.write(f"CMM {self.SMU_Source},1")
        self.Ana.write(f"CMM {self.SMU_Substrate},1")

    def configure_current_ranging(self):

        self.Ana.write(f"RI {self.SMU_Gate},13")
        self.Ana.write(f"RI {self.SMU_Drain},0")
        self.Ana.write(f"RI {self.SMU_Source},0")
        self.Ana.write(f"RI {self.SMU_Substrate},0")

    def Set_Compliance(self, Id=15E-3, Ig = 1E-4, Ib=15E-3):

        self.Igcomp = Ig
        self.Idcomp = Id
        self.Ibcomp = Ib

    def Bias(self):

         # SOURCE BIAS:
        self.Ana.write(f'DV {self.SMU_Source},12,{self.Vs},{self.Idcomp}')
        # DRAIN BIAS:
        self.Ana.write(f'DV {self.SMU_Drain},12,{self.Vds},{self.Idcomp}')
        # SUBSTRATE BIAS:
        self.Ana.write(f'DV {self.SMU_Substrate},12,{self.Vb},{self.Ibcomp}')

    def Configure(self):

        self.reset_Analyzer()
        self.Enable_Channels()
        self.configure_measurement()
        self.configure_current_ranging()

    def Step_Gate_Voltage(self, Vg):
        self.Ana.write(f'DV {self.SMU_Gate},0,{Vg},{self.Igcomp}')

    def Measure_Currents(self):
        self.Ana.write(f'TI {self.SMU_Drain} ,11')
        Id = self.Ana.query('RMD?')
        Id = Id.rstrip('\n')
        self.Ana.write(f'TI {self.SMU_Source} ,11')
        Is = self.Ana.query('RMD?')
        Is = Is.rstrip('\n')
        self.Ana.write(f'TI {self.SMU_Gate} ,11')
        Ig = self.Ana.query('RMD?')
        Ig = Ig.rstrip('\n')
        self.Ana.write(f'TI {self.SMU_Substrate} ,11')
        Ib = self.Ana.query('RMD?')
        Ib = Ib.rstrip('\n')
        return(Id,Is,Ig,Ib)


if (__name__ == '__main__'):
    E4980A = LCR()
    E4980A.configure()
    A4156C = Analyzer()

