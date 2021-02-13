# Azure IoT Edge Dev Tool

[![PyPI version](https://badge.fury.io/py/iotedgedev.svg)](https://badge.fury.io/py/iotedgedev)

The **IoT Edge Dev Tool** greatly simplifies [Azure IoT Edge](https://azure.microsoft.com/en-us/services/iot-edge/) development down to simple commands driven by environment variables.

 - It gets you started with IoT Edge development with the [IoT Edge Dev Container](https://hub.docker.com/r/microsoft/iotedgedev/) and IoT Edge solution scaffolding that contains a default module and all the required configuration files.
 - It speeds up your inner-loop dev (dev, debug, test) by reducing multi-step build & deploy processes into one-line CLI commands as well as drives your outer-loop CI/CD pipeline. _You can use all the same commands in both stages of your development life-cycle._
 - This repo is based on [Azure IoT Edge Dev Github](https://github.com/Azure/iotedgedev)

## Overview
For the absolute fastest way to get started with IoT Edge Dev, please see the [Quickstart](#quickstart) section below.

For a more detailed overview of IoT Edge Dev Tool including setup and commands, please see the [Wiki](https://github.com/Azure/iotedgedev/wiki).

## Quickstart

This quickstart will run a vscode devcontainer, setup Azure resources, build and deploy modules to your device, setup and start the IoT Edge simulator, monitor messages flowing into IoT Hub, and finally deploy to the IoT Edge runtime.

<!-- Here's a 3 minute video walk-through of this Quickstart:

[![Azure IoT Edge Dev Tool: Quickstart](assets/edgedevtoolquickstartsmall.png)](https://aka.ms/iotedgedevquickstart) -->

The only thing you need to install is Docker. All of the other dev dependencies are included in the container. 

0. **Pre requisites**

    - Docker Desktop
    - VSCode with Remote-containers extention installed

1. **Clone this repo to a local folder**

    - Just use the regular way to repo your folder.

1. **Open VSCode**

    - Open VSCode in the cloned folder
    - VSCode will detect the devcontainer definition and ask to reopen in devcontainer, press accept
    - Copy the `.env.tmp` file as `.env`  

    > The solution comes with a default python module named `filterModule`

    <details>
    <summary>More information</summary>

    1. You will see structure of current folder like below:

    ```
        │  .env.tmp
        │  .gitignore
        │  deployment.debug.template.json
        │  deployment.template.json
        │
        ├─.vscode
        │      launch.json
        │
        └─modules
            └─filtermodule
                │  .gitignore
                │  Dockerfile.amd64
                │  Dockerfile.amd64.debug
                │  Dockerfile.arm32v7
                │  Dockerfile.arm32v7.debug
                │  Dockerfile.arm64v8
                │  Dockerfile.arm64v8.debug
                │  main.py
                |  module.json
                │  requirements.txt
    ```
    3. Open `deployment.template.json` file   
        1. You will see below section in the modules section:

        ```
        "filtermodule": {
            "version": "1.0",
            "type": "docker",
            "status": "running",
            "restartPolicy": "always",
            "settings": {
                "image": "${MODULES.filtermodule}",
                "createOptions": {}
            }
        }
        ```

        2. Two default routes are added:
        
        ```
        "routes": {
            "sensorTofiltermodule": "FROM /messages/modules/tempSensor/outputs/temperatureOutput INTO BrokeredEndpoint(\"/modules/filtermodule/inputs/input1\")",
            "filtermoduleToIoTHub": "FROM /messages/modules/filtermodule/outputs/* INTO $upstream"
        }
        ```
    </details>

1. **Initialize IoT Edge solution and setup Azure resources**

    `iotedgedev iothub setup`

    > `iotedgedev iothub setup` will setup your Azure IoT Hub in a single command.

    1. Open `.env` file, you will see the `IOTHUB_CONNECTION_STRING` and `DEVICE_CONNECTION_STRING` environment variables filled correctly.


1. **Build IoT Edge module images**

    `sudo iotedgedev build`
    
    > This step will build user modules in deployment.template.json targeting amd64 platform.

    <details>
    <summary>More information</summary>

    1. You will see a "BUILD COMPLETE" for each module and no error messages in the terminal output.
    1. Open `config/deployment.amd64.json` file, you will see the module image placeholders expanded correctly.
    1. Run `sudo docker image ls`, you will see the module images you just built.

    </details>

1. **Setup and start the IoT Edge Simulator to run the solution**

    `sudo iotedgedev start --setup --file config/deployment.amd64.json`

    <details>
    <summary>More information</summary>

    1. You will see an "IoT Edge Simulator has been started in solution mode." message at the end of the terminal output
    2. Run `sudo docker ps`, you will see your modules running as well as an edgeHubDev container

    </details>

1. **Monitor messages sent from IoT Edge Simulator to IoT Hub**

    `iotedgedev monitor`

    <details>
    <summary>More information</summary>

    1. You will see your expected messages sending to IoT Hub

    </details>

## Resources
Please refer to the [Wiki](https://github.com/Azure/iotedgedev/wiki) for details on setup, usage, and troubleshooting.

## Data/Telemetry
This project collects usage data and sends it to Microsoft to help improve our products and services. Read our [privacy statement](http://go.microsoft.com/fwlink/?LinkId=521839) to learn more. 
If you don’t wish to send usage data to Microsoft, you can change your telemetry settings by updating `collect_telemetry` to `no` in `~/.iotedgedev/settings.ini`.

## Contributing
This project welcomes contributions and suggestions. Please refer to the [Contributing file](CONTRIBUTING.md) for details on contributing changes.

Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.