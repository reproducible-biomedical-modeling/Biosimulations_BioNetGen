#!/opt/conda/bin/python
import argparse, libsedml, subprocess, os, shutil, re
import pandas as pd

class BNGRunner:
    def __init__(self):
        self._parse_args()

    def _parse_args(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--model", dest="model_file", help="Model BNGL or XML file")
        self.parser.add_argument("--sim", dest="simulation_file", help="SED-ML file with simulation details")
        self.parser.add_argument("--results", dest="output_path", help="Output path to write results to")
        self.parser.add_argument("--bng_path", dest="bng_path", default="/home/BNGDocker/bionetgen/bng2/BNG2.pl", 
                                        help="Path to BNG2.pl")
        self.args = self.parser.parse_args()

    def read_gdat(self, model_path):
        with open(model_path, "r") as f:
            # Get column names from first line of file
            line = f.readline()
            names = re.split('\s+',(re.sub('#','',line)).strip())
            gdat = pd.read_table(f,sep='\s+',header=None,names=names)
            # Set the time as index
            gdat = gdat.set_index("time")
        return gdat

    def pass_results(self, model_name, output_path):
        # load gdat
        data = self.read_gdat(model_name + ".gdat")
        print(data)
        data.to_csv(os.path.join(output_path, model_name+".csv"))


    def adjust_bngl(self, bngl_file, sedml_file):
        # TODO: edit BNGL according to SED-ML
        return bngl_file

    def run(self):
        # for now testing purposes, we'll just write stuff out
        print(self.args)
        # now let's start running sim
        os.mkdir("/home/BNGDocker/sim")
        os.chdir("/home/BNGDocker/sim")
        # get the simulation names in here
        # TODO: Add checks to make sure this exists and a bngl file
        model_file_name = os.path.basename(self.args.model_file)
        model_name = model_file_name.replace(".bngl","")
        sim_file_name = os.path.basename(self.args.simulation_file)
        sim_name = sim_file_name.replace(".bngl","")
        # moving files 
        shutil.move(self.args.model_file, model_file_name)
        shutil.move(self.args.simulation_file, sim_file_name)
        print(os.listdir())
        # adjusting the bngl file
        adjusted_file = self.adjust_bngl(model_file_name, sim_file_name)
        # running simulation
        subprocess.call([self.args.bng_path, adjusted_file])
        print(os.listdir())
        # put files into output path
        os.mkdir(self.args.output_path)
        self.pass_results(model_name, self.args.output_path)
        # check if saved
        os.chdir(self.args.output_path)
        print(os.listdir())

if __name__ == "__main__":
    p = BNGRunner()
    p.run()
