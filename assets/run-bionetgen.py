#!/opt/conda/bin/python
import argparse 

class BNGRunner:
    def __init__(self):
        self._parse_args()

    def _parse_args(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--model", dest="model_file", help="Model BNGL or XML file")
        self.parser.add_argument("--sim", dest="simulation_file", help="SED-ML file with simulation details")
        self.parser.add_argument("--results", dest="output_path", help="Output path to write results to")
        self.parser.add_argument("--bng_path", dest="bng_path", default="", 
                                        help="Path to BNG2.pl")
        self.args = self.parser.parse_args()

    def run(self):
        # for now testing purposes, we'll just write stuff out
        print(self.args)

if __name__ == "__main__":
    p = BNGRunner()
    p.run()
