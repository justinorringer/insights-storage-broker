# Insights Storage Broker

The Insights Storage Broker microservice is responsible for moving uploaded packages from the staging to rejected storage bucket in the event the file fails validation. It will also advertise successful payloads to the platform via the `platform.upload.available` topic. It reads from the `platform.upload.validation` topic by default.

## How it Works

Standard Workflow
![UML](http://www.plantuml.com/plantuml/png/hLAxRjmm4Epr5GlMbWzvL48W6EbI94tQ0C8UjISpvaFXBXKSZFnxI4idMxX74KG50N5dPdU6-y22KPApyCMp6Hw5uRk4Y0F1vnYUA5PZhXjjHlG24rhJenW_T4nnCfegycBa2AD5EOJekZJQW7rtGWQ_4U1PkzlFsbV8EA6nkBTKPGdS8rCclj2IVY9vlOtqaxIShi-dgzlhSpN0IMjYtXrojnG9NFx9NIgqCjUeXpS-87_VWX34aXE4muKu6dXMaNubOkbChnfGkDTz_UxzXu_gxeTNhtAbjWoW_XJj6n7MxJQtTVHrvCBVOkhsQgeDO3zH5CFaoByuMMimuh6WBxYzeVVyAMIOyMZ1yG0wUCd2xHse56rn-YWoShFRuM--dr_hFbUoSR9CK1xWF6l_NxDU7laVibwODxD-kvvDzZyUy-4S-aj1Ri7gQvY8Jxc3X6MhOGQe8h2XrErcxPkLMjfMb5i-v2Cv-nS0 "Insights Storage Broker")

Insights Storage Broker consumes from the `platform.upload.validation` topic. If the payload has succeeded validation, the storage broker will pass the message along with a download url to the `platform.upload.available` topic so that other services on the platform can consume it. Storage broker expects to recieve **all** the data in the message that the validation service originally recieved in addition to the the `validation` key.

If a failure message is recieved, Storage Broker will copy the file to the rejected bucket and not advertise the availability of the payload to the platform.

Advisor Workflow

![UML](http://www.plantuml.com/plantuml/png/XP8nRiCm34Ltdu8Ny0Ko646cPkdIxePYCpPHMIH4AeLlNoiAYjfjwa63GFxtFoaTrLoqD7au1wLXD8Ktu-W6X5Fa3uoLB7NgI5mma2J6N64miXd4Exjod5eADmoBQcv7LbkkGqJLbVBbTDwJuM-LbYZjfKJP0f9uTdthRewyktYiIhwwsKbsU0m2Yg5NqDHrg7fD7iJD6Gd6zyGxdBh9JSjvxeZ5CDF0zJUCHeeA0Jz_Ujc8aDlhqWx6GbtrFxDkrjivR1uE8hfUx-WLTQsgcwVR_0CewU99HopO2LLp-J70j_1XzCg64FEV0hx2DkpxI7dp8Xoju3mEhfj1ID1JmEg8eK-J_m80 "Insights Advisor Workflow")

The advisor workflow is slightly different. Advisor payloads are processed and sent directly to Host Based Inventory (HBI) to be handled. HBI will pass these successful payloads to the `platform.inventory.host-egress` topic. Services that are not reading from this topic yet may still expect new payloads to be announced on `platform.upload.available`. In order to support these, storage broker will read the HBI announcements and then republish them on `platform.upload.available` in the expected legacy format.

## Messages

Available Message:

      {
          "account": <account number>,
          "request_id": <uuid for the payload>,
          "principal": <currently the org ID>,
          "service": <the service that validated the payload>,
          "category": <a category for the payload>,
          "url": <URL to download the file>,
          "b64_identity": <the base64 encoded identity of the sender>,
          "id": <host based inventory id if available>, **RELOCATING TO EXTRAS**
          "satellite_managed": <boolean if the system is managed by satellite>, **RELOCATING TO EXTRAS**
          "timestamp": <the time the available message was put on the topic>,
          "validation": <success|failure>,
          "size": <size in bytes of payload>,
          "metadata": <metadata attached to the original upload>,
          "extras": {
              "satellite_managed": <same as above>
              "id": <same as above>
              ...
          }
      }

## Authors

Stephen Adams - Initial Work - [SteveHNH](https://www.github.com/SteveHNH)
