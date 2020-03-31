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
        # save to csv
        data.to_csv(os.path.join(output_path, model_name+".csv"))


    def adjust_bngl(self, bngl_file, sedml_file):
        adjusted_file = "adjusted.bngl"
        # TODO: edit BNGL according to SED-ML
        # first read the BNGL file, only the model
        with open(bngl_file, "r") as f:
            line = f.readline()
            bngl_lines = []
            while line.strip() != "end model":
                bngl_lines.append(line)
                line = f.readline()
            bngl_lines.append(line)
        # now read SED-ML
        sedml = libsedml.readSedMLFromFile(sedml_file)
        sim_xml = sedml.getSimulation(0)
        # get initial time, end time and number of points
        init = sim_xml.getOutputStartTime()
        end  = sim_xml.getOutputEndTime() 
        pts  = sim_xml.getNumberOfPoints()
        # let's check the algorithm name we want to use
        alg = sim_xml.getAlgorithm()
        ann = alg.getAnnotation()
        name_rdf = ann.getChild(0).getChild(0).getChild(0)
        # make sure we got the name attr
        assert name_rdf.getAttrValue(0) == "name", "Can't find name annotation" 
        alg_name = name_rdf.getChild(0).toXMLString()
        # import IPython
        # IPython.embed()
        if alg_name == "CVODE":
            method_name = "ode"
        else:
            print("this algorithm is not supported: {}".format(alg_name))
        # now let's add the appropriate lines to the bngl
        if method_name == "ode":
            bngl_lines += "generate_network({overwrite=>1})\n"
            bngl_lines += 'simulate({' + 'method=>"{}",t_start=>{},t_end=>{},n_steps=>{}'.format(method_name, init, end, pts) + '})\n'
        # TODO: Get algorithm parameters and use them properly
        # num_params = alg.getNumAlgorithmParameters()
        # for np in range(num_params):
        #     param = alg.getNumAlgorithmParameter(np)
        with open(adjusted_file, "w") as f:
            f.writelines(bngl_lines)
        return adjusted_file

    def run(self):
        # for now testing purposes, we'll just write stuff out
        print(self.args)
        # get the simulation names in here
        # TODO: Add checks to make sure this exists and a bngl file
        model_file_name = os.path.basename(self.args.model_file)
        model_name = model_file_name.replace(".bngl","")
        sim_file_name = os.path.basename(self.args.simulation_file)
        sim_name = sim_file_name.replace(".bngl","")
        # moving files 
        # TODO: determine a logical way to deal with these
        shutil.copy(self.args.model_file, self.args.output_path)
        shutil.copy(self.args.simulation_file, self.args.output_path)
        os.chdir(self.args.output_path)
        print(os.listdir())
        # adjusting the bngl file
        adjusted_file = self.adjust_bngl(model_file_name, sim_file_name)
        # running simulation
        subprocess.call([self.args.bng_path, adjusted_file])
        print(os.listdir())
        # put files into output path
        self.pass_results(model_name, os.getcwd())
        # check if saved
        print(os.listdir())

if __name__ == "__main__":
    p = BNGRunner()
    p.run()
