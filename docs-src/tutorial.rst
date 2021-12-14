Tutorial
========

BioSimulators-BioNetGen is available as a command-line program and as a command-line program encapsulated into a Docker image.


Creating COMBINE/OMEX archives and encoding simulation experiments into SED-ML
------------------------------------------------------------------------------

Information about how to create COMBINE/OMEX archives which can be executed by BioSimulators-BioNetGen is available `here <https://docs.biosimulations.org/users/creating-projects/>`_.

A list of the algorithms and algorithm parameters supported by BioNetGen is available at `BioSimulators <https://biosimulators.org/simulators/bionetgen>`_.


Targets for encoding changes to model parameters into SED-ML
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The following targets should be used to encode changes to model parameters into SED-ML.

* Compartment sizes: targets should follow the pattern ``compartments.<compartment_id>.size``. E.g.::

    <sedml:changeAttribute target="compartments.Compartment_C.size" newValue="1e-6" />

* Function expressions: targets should follow the pattern ``functions.<function_id>.expression``. E.g.::

    <sedml:changeAttribute target="functions.gfunc.expression" newValue="0.5" />

* Function arguments and expressions: targets should follow the pattern ``functions.<function_id>(<args>).expression``. E.g.::

    <sedml:changeAttribute target="functions.gfunc().expression" newValue="0.5" />

* Initial species counts: targets should follow the pattern ``species.<species_id>.initialCount``. E.g.::

    <sedml:changeAttribute target="species.GeneA_00().initialCount" newValue="10" />

* Parameter values: targets should follow the pattern ``parameters.<parameter_id>.value``. E.g.::

    <sedml:changeAttribute target="parameters.k_1.value" newValue="2.0" />


Targets for encoding the desired observables into SED-ML
++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The following patterns should be used to encode the desired observables of a simulation into SED-ML.

* Species: targets for species counts and concentrations should follow the pattern ``species.<species_id>.count``. E.g.::

    <sedml:dataGenerator id="data_generator_species_A">
      <listOfVariables>
        <sedml:Variable id="variable_species_A" target="species.A().count" taskReference="taskId" />
      </listOfVariables>
      <math xmlns="http://www.w3.org/1998/Math/MathML">
        <ci>variable_species_A</ci>
      </math>
    </sedml:dataGenerator>

* Molecules: targets for molecule counts and concentrations should follow the pattern ``molecules.<molecule_pattern>.count``. E.g.::

    <sedml:dataGenerator id="data_generator_molecule_B">
      <listOfVariables>
        <sedml:Variable id="variable_molecule_B" target="molecules.B().count" taskReference="taskId" />
      </listOfVariables>
      <math xmlns="http://www.w3.org/1998/Math/MathML">
        <ci>variable_molecule_B</ci>
      </math>
    </sedml:dataGenerator>


Command-line program
--------------------

The command-line program can be used to execute COMBINE/OMEX archives that describe simulations as illustrated below.

.. code-block:: text

    usage: bionetgen [-h] [-d] [-q] -i ARCHIVE [-o OUT_DIR] [-v]

    BioSimulators-compliant command-line interface to the BioNetGen <https://bionetgen.org> simulation program.

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           full application debug mode
      -q, --quiet           suppress all console output
      -i ARCHIVE, --archive ARCHIVE
                            Path to OMEX file which contains one or more SED-ML-
                            encoded simulation experiments
      -o OUT_DIR, --out-dir OUT_DIR
                            Directory to save outputs
      -v, --version         show program's version number and exit

For example, the following command could be used to execute the simulations described in ``./modeling-study.omex`` and save their results to ``./``:

.. code-block:: text

    bionetgen -i ./modeling-study.omex -o ./


Docker image with a command-line entrypoint
-------------------------------------------

The entrypoint to the Docker image supports the same command-line interface described above.

For example, the following command could be used to use the Docker image to execute the same simulations described in ``./modeling-study.omex`` and save their results to ``./``:

.. code-block:: text

    docker run \
        --tty \
        --rm \
        --mount type=bind,source="$(pwd),target=/tmp/working-dir \
        ghcr.io/biosimulators/bionetgen:latest \
            -i /tmp/working-dir/modeling-study.omex \
            -o /tmp/working-dir
