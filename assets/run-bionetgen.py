#!/opt/conda/bin/python
import argparse, libsedml, subprocess, os, shutil, re
import pandas as pd

class BNGRunner:
    def __init__(self, adjusted_name="sedml_adjusted"):
        self._parse_args()
        self.adjusted_name = adjusted_name
        self.adjusted_file = self.adjusted_name + ".bngl"

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

    def pass_results(self, input_name, output_path):
        # load gdat
        data = self.read_gdat(input_name + ".gdat")
        print(data)
        # save to csv
        print(output_path, self.model_name)
        data.to_csv(self.model_name +".csv")

    def get_bngl_lines(self, bngl_file):
        with open(bngl_file, "r") as f:
            line = f.readline()
            bngl_lines = []
            # TODO: end model is not necessary, find other
            # ways to check for the action block
            while line.strip() != "end model":
                bngl_lines.append(line)
                line = f.readline()
            bngl_lines.append(line)
        return bngl_lines

    def get_time_values(self, sim_xml):
        init = sim_xml.getOutputStartTime()
        end  = sim_xml.getOutputEndTime() 
        pts  = sim_xml.getNumberOfPoints()
        return (init, end, pts)

    def get_method_name(self, alg_xml):
        # TODO: get it from KISAO ID
        # 19 - CVODE/ODE
        # 29 - SSA/Gillespie
        # 263 - NFSim
        kisao_ID = alg_xml.getKisaoID()
        kisao_num = int(kisao_ID.split(":")[1])
        # check algorithm type
        if kisao_num == 19:
            # CVODE/ODE
            method_name = "ode"
        elif kisao_num == 29:
            # SSA/Gillespie
            method_name = "ssa"
        elif kisao_num == 263:
            # NFSim
            method_name = "nfsim"
        else:
            print("this algorithm with KISAO ID {} is not supported".format(kisao_ID))
        return method_name

    def get_parameter_changes(self, model_xml):
        list_of_changes = model_xml.getListOfChanges()
        bngl_parameter_changes = []
        for num_change in range(list_of_changes.getNumChanges()):
            # getting the change xml
            change_xml = list_of_changes.get(num_change)
            # name of the parameter
            target = change_xml.getTarget()
            # TODO: Fix this hacky mess
            target = target.split("id=")[1].split("]")[0].replace("'","")
            # value we are setting it to
            value = float(change_xml.getNewValue())
            # append to the list of changes
            bngl_parameter_changes.append( (target, value) )
        return bngl_parameter_changes

    def get_method_parameters(self, alg_xml):
        method_parameters = []
        # Loop over all given parameters
        num_params = alg_xml.getNumAlgorithmParameters()
        for nparam in range(num_params):
            param_xml = alg_xml.getAlgorithmParameter(nparam)
            # get kisao ID
            kisao_int = param_xml.getKisaoIDasInt()
            param_val = param_xml.getValue()
            if kisao_int == 211:
                # Relative tolerance
                method_parameters.append( ("rtol", param_val) )
            elif kisao_int == 209:
                # Absolute tolerance
                method_parameters.append( ("atol", param_val) )
            else:
                print("Parameter of KISAO ID {} is not supported".format(param_xml.getKisaoID()))
        return method_parameters

    def adjust_bngl(self, bngl_file, sedml_file):
        # first read the BNGL file, only the model
        bngl_lines = self.get_bngl_lines(bngl_file)
        # now read SED-ML
        sedml = libsedml.readSedMLFromFile(sedml_file)
        # TODO: As the standard changes this block of code needs to be 
        # adapted. Currently assumes a single time series
        sim_xml = sedml.getSimulation(0)
        # get initial time, end time and number of points
        init, end, pts = self.get_time_values(sim_xml)
        # let's check the algorithm name we want to use
        alg_xml = sim_xml.getAlgorithm()
        method_name = self.get_method_name(alg_xml)
        # Get algorithm parameters and use them properly
        method_parameters = self.get_method_parameters(alg_xml)

        # TODO: Get simulation parameter changes and apply them 
        # properly
        model_xml = sedml.getModel(0)
        bngl_parameter_changes = self.get_parameter_changes(model_xml)

        # add setParameter command to the bngl
        for change in bngl_parameter_changes:
            t,v = change
            bngl_lines += 'setParameter("{}",{})\n'.format(t,v)

        # now let's add the appropriate lines to the bngl
        if method_name == "ode":
            bngl_lines += "generate_network({overwrite=>1})\n"
            simulate_line = 'simulate({' + 'method=>"{}",t_start=>{},t_end=>{},n_steps=>{}'.format(method_name, init, end, pts) 
            for mp in method_parameters:
                param, val = mp
                simulate_line += ",{}=>{}".format(param,val)
            simulate_line += '})\n'
            bngl_lines += simulate_line
        elif method_name == "ssa":
            bngl_lines += "generate_network({overwrite=>1})\n"
            simulate_line = 'simulate({' + 'method=>"{}",t_start=>{},t_end=>{},n_steps=>{}'.format(method_name, init, end, pts) 
            # Add method parameters here if we support it in the future
            simulate_line += '})\n'
            bngl_lines += simulate_line
        elif method_name == "nfsim":
            simulate_line = 'simulate({' + 'method=>"{}",t_start=>{},t_end=>{},n_steps=>{}'.format(method_name, init, end, pts) 
            # Add method parameters here if we support it in the future
            simulate_line += '})\n'
            bngl_lines += simulate_line
        # write adjusted bngl file
        with open(self.adjusted_file, "w") as f:
            f.writelines(bngl_lines)
        return self.adjusted_file

    def run(self):
        # for now testing purposes, we'll just write stuff out
        print(self.args)
        # get the simulation names in here
        # TODO: Add checks to make sure this exists and a bngl file
        model_file_name = os.path.basename(self.args.model_file)
        model_name = model_file_name.replace(".bngl","")
        self.model_name = model_name 
        sim_file_name = os.path.basename(self.args.simulation_file)
        sim_name = sim_file_name.replace(".xml","")
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
        self.pass_results(self.adjusted_name, self.args.output_path)
        # check if saved
        print(os.listdir())

if __name__ == "__main__":
    p = BNGRunner()
    p.run()
