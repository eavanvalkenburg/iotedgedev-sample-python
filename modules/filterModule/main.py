# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import logging
import ast
import asyncio
import os

from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse

TEMP_THRESHOLD_PROPERTY_NAME = os.environ.get("TEMP_THRESHOLD_PROPERTY_NAME")
TEMP_THRESHOLD_VERSION_NAME = TEMP_THRESHOLD_PROPERTY_NAME + "_version"
TEMP_THRESHOLD_STATUS_NAME = TEMP_THRESHOLD_PROPERTY_NAME + "_status"
DESIRED_PROPERTY_KEY = "desired"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class FilterModule(IoTHubModuleClient):
    def __init__(self, mqtt_pipeline, http_pipeline):
        """Initialize the filtermodule, this is based on the IoTHubModuleClient."""
        super().__init__(mqtt_pipeline=mqtt_pipeline, http_pipeline=http_pipeline)
        self.temperature_threshold = 0
        self.temperature_threshold_version = None
        self.shutdown_flag = False

        self.on_message_received = self.message_router
        self.on_twin_desired_properties_patch_received = self.twin_patch_handler
        self.on_method_request_received = self.method_request_router

    async def async_run(self):
        """Does all the startup work and doesn't stop.

        Connect the client.
        Get the desired twin settings and parse those.
        Update the reported twin settings.
        Wait for shutdown_flag to be set and then shutdown.
        """
        await self.connect()
        twin = await self.get_twin()
        logger.debug("Twin: %s", twin)
        await self.twin_patch_handler(twin.get(DESIRED_PROPERTY_KEY), False)
        await self.update_reported_properties()

        def shutdown_listener():
            """Check if the shutdown_flag was set every 10 seconds."""
            while not self.shutdown_flag:
                time.sleep(10)

        loop = asyncio.get_running_loop()
        shutdown_list = loop.run_in_executor(None, shutdown_listener)
        await shutdown_list

        await self.shutdown()

    async def message_router(self, message):
        """Handle all messages.

        Route the message to the right function based on input_name.
        """
        logger.debug("Received message on input %s", message.input_name)
        if message.input_name == "input1":
            await self.message_handler_input1(message)
        else:
            logger.warning("Message received on unknown input, ignoring.")

    async def message_handler_input1(self, message):
        """Handle input1 messages."""
        dict_str = message.data.decode("UTF-8")
        message_data = ast.literal_eval(dict_str)
        if self.filter_temperature(message_data):
            await self.send_message_to_output(message, "output1")

    def filter_temperature(self, message_data):
        """Returns true or false if the temperature field is above or below the threshold."""
        if (
            message_data.get("machine", {}).get("temperature")
            > self.temperature_threshold
        ):
            return True
        return False

    async def update_temperature_threshold(
        self, new_temp, version, update_reported=True
    ):
        """Update the temperature threshold and update the reported twin, if the value is the same, just return"""
        if version == self.temperature_threshold_version:
            return
        self.temperature_threshold = new_temp
        self.temperature_threshold_version = version
        if update_reported:
            await self.update_reported_properties()

    async def update_reported_properties(self):
        """Update the reported twin."""
        reported_properties = {
            TEMP_THRESHOLD_PROPERTY_NAME: self.temperature_threshold,
            TEMP_THRESHOLD_VERSION_NAME: self.temperature_threshold_version,
            TEMP_THRESHOLD_STATUS_NAME: "deployed",
        }
        logger.debug(
            "Setting reported temperature to %s, from version: %s",
            reported_properties[TEMP_THRESHOLD_PROPERTY_NAME],
            reported_properties[TEMP_THRESHOLD_VERSION_NAME],
        )
        await self.patch_twin_reported_properties(reported_properties)

    async def twin_patch_handler(self, patch, update_reported=True):
        """Handle twin patches, assumption is only the desired field."""
        logger.info("New twin settings received: %s", patch)
        await self.update_temperature_threshold(
            patch.get(TEMP_THRESHOLD_PROPERTY_NAME, self.temperature_threshold),
            patch.get("$version"),
            update_reported,
        )

    async def method_request_router(self, method_request):
        """Handle direct method requests."""
        logger.debug("Request: %s", method_request)
        if method_request.name == "shutdown":
            await self.method_handler_shutdown(method_request)
        else:
            logger.warning(
                "Unknown method request received: %s, with id: %s",
                method_request.name,
                method_request.request_id,
            )
            await self.send_method_response(
                MethodResponse(method_request.request_id, 200, method_request.payload)
            )

    async def method_handler_shutdown(self, method_request):
        """Handle a shutdown request."""
        logger.debug(
            "Shutting down because of method request, id: %s", method_request.request_id
        )
        await self.send_method_response(
            MethodResponse.create_from_method_request(
                method_request, 200, payload={"shutdown": True}
            )
        )
        self.shutdown_flag = True


if __name__ == "__main__":
    filter_module = FilterModule.create_from_edge_environment()
    asyncio.run(filter_module.async_run())
