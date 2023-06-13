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

ALL_SCEN_FILES = glob_wildcards(
    "Shuntyard-Instance-Generator/quasi_real_instances/exp/{exp}/{layout}/{scenario_name}.scen"
)
ALL_GRAPH_FILES = glob_wildcards(
    "Shuntyard-Instance-Generator/quasi_real_instances/exp/{exp}/{layout}/{graph_name}.graph"
)
ALL_PB_SCEN_FILES = expand(
    "mapf_protobuf_format_instances/{exp}/{layout}/{scenario_name}.scen.pb",
    zip,
    exp=ALL_SCEN_FILES.exp,
    layout=ALL_SCEN_FILES.layout,
    scenario_name=ALL_SCEN_FILES.scenario_name,
)
ALL_PB_GRAPH_FILES = expand(
    "mapf_protobuf_format_instances/{exp}/{layout}/{graph_name}.graph.pb",
    zip,
    exp=ALL_GRAPH_FILES.exp,
    layout=ALL_GRAPH_FILES.layout,
    graph_name=ALL_GRAPH_FILES.graph_name,
)
print(ALL_GRAPH_FILES)


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
    "ShuntYard-Instance-Generator/quasi_real_instances/exp/{exp}/{layout}/{scenario_or_graphname}.{ext}"
)


checkpoint create_instances:
    conda:
        "../../Shuntyard-Instance-Generator/environment.yml"
    output:
        "Shuntyard-Instance-Generator/quasi_real_instances/exp/1a/shuffleboard_arrival_0t_50n_3b_20g_0.0r/shuffleboard_arrival_0t_50n_3b_20g_0.0r_2a_0gs_0ss_0types_0.scen",
    shell:
        "cd ShuntYard-Instance-Generator && python main.py"
