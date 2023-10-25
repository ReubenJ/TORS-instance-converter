# Globs all the proto files from either the cTORS or Shuntyard-Instance-Generator folder
PROTOS = glob_wildcards(
    "{source,(cTORS|Shuntyard-Instance-Generator)}/protos/{name}.proto"
)
PROTO_FILES = expand(
    "protos/{source}/{name}.proto", zip, source=PROTOS.source, name=PROTOS.name
)
COMPILED_PROTOS = expand("protos/{name}_pb2.py", name=PROTOS.name)
COMPILED_FOLDER = "protos"

SCEN_FILE = "Shuntyard-Instance-Generator/quasi_real_instances/exp/1a/shuffleboard_arrival_0t_50n_3b_20g_0.0r/shuffleboard_arrival_0t_50n_3b_20g_0.0r_2a_0gs_0ss_0types_0.scen"


rule copy_protos:
    input:
        "{source}/protos/{name}.proto",
    output:
        "protos/{source}/{name}.proto",
    shell:
        "mkdir -p protos && cp {input} {output}"


rule generate_python_protobuf:
    input:
        PROTO_FILES,
    output:
        filename="protos/{name}_pb2.py",
        pyi="protos/{name}_pb2.pyi",
    shell:
        "mkdir -p {COMPILED_FOLDER} && protoc --python_out={COMPILED_FOLDER} --pyi_out={COMPILED_FOLDER} {input} "
        "-I protos/cTORS -I protos/Shuntyard-Instance-Generator"


EXPERIMENTS, LAYOUTS, _, EXTS = glob_wildcards(
    "Shuntyard-Instance-Generator/quasi_real_instances/exp/{exp}/{layout}/{scenario_or_graphname}.{ext}"
)


checkpoint create_instances:
    input:
        COMPILED_PROTOS[0],
        "Shuntyard-Instance-Generator/settings.ini",
    output:
        sentinel=SCEN_FILE,
        all_files=directory("Shuntyard-Instance-Generator/quasi_real_instances"),
    shell:
        "cd Shuntyard-Instance-Generator && python main.py"
