import time
import logging
import ast
import asyncio
import os
import socket

# pylint: disable=E0611
from six.moves import input
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse

TEMP_THRESHOLD_PROPERTY_NAME = os.environ.get("TEMP_THRESHOLD_PROPERTY_NAME")
TEMP_THRESHOLD_VERSION_NAME = f"{TEMP_THRESHOLD_PROPERTY_NAME}_version"
TEMP_THRESHOLD_STATUS_NAME = f"{TEMP_THRESHOLD_PROPERTY_NAME}_status"
LOCAL_IP = "local_ip_address"
DESIRED_PROPERTY_KEY = "desired"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class FilterModule:
    def __init__(self, client: IoTHubModuleClient):
        """Initialize the filtermodule, this is based on the IoTHubModuleClient."""
        self.client = client
        self.temperature_threshold = 25
        self.temperature_threshold_version = None
        self.shutdown_flag = False

        self.client.on_message_received = self.message_router
        self.client.on_twin_desired_properties_patch_received = self.twin_patch_handler
        self.client.on_method_request_received = self.method_request_router

    async def async_run(self):
        """Does all the startup work and doesn't stop.

        Connect the client.
        Get the desired twin settings and parse those.
        Update the reported twin settings.
        Wait for shutdown_flag to be set and then shutdown.
        """
        self.shutdown_flag = False
        await self.client.connect()
        twin = await self.client.get_twin()
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

        await self.client.shutdown()

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
            await self.client.send_message_to_output(message, "output1")

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
            LOCAL_IP: socket.gethostbyname(socket.gethostname()),
        }
        logger.debug(
            "Setting reported temperature to %s, from version: %s",
            reported_properties[TEMP_THRESHOLD_PROPERTY_NAME],
            reported_properties[TEMP_THRESHOLD_VERSION_NAME],
        )
        await self.client.patch_twin_reported_properties(reported_properties)

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
            await self.client.send_method_response(
                MethodResponse(method_request.request_id, 200, method_request.payload)
            )

    async def method_handler_shutdown(self, method_request):
        """Handle a shutdown request."""
        logger.debug(
            "Shutting down because of method request, id: %s", method_request.request_id
        )
        await self.client.send_method_response(
            MethodResponse.create_from_method_request(
                method_request, 200, payload={"shutdown": True}
            )
        )
        self.shutdown_flag = True


if __name__ == "__main__":
    client = IoTHubModuleClient.create_from_edge_environment()
    filter_module = FilterModule(client)
    asyncio.run(filter_module.async_run())
