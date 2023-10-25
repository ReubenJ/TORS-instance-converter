# TORS-instance-converter

This project's environment is managed using [`devbox`](https://www.jetpack.io/devbox). You have 2 options for getting the project running:

 - devcontainer: If you use VSCode, this is the most straightforward option. Install the [devcontainer](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) plugin and open the project. Then run the command, "Dev Containers: Reopen Folder in Container".
 - `devbox`: if you want to make changes to the environment, you should have devbox installed. Refer to their documentation for [installation](https://www.jetpack.io/devbox/docs/installing_devbox/) and [getting started](https://www.jetpack.io/devbox/docs/quickstart/).

 ## Once up and running

 To create/convert the instances, run the following twice:

 ```shell
 snakmake --cores all
 ```

 Alternatively, you can use fewer cores (ex: `--cores 2`). The first time you run the `snakemake` command should create a directory called `mapf_protobuf_format_instances`, the second run should create a directory of the converted TORS instances called `tors_instances`.