# Insights Storage Broker

The Insights Storage Broker microservice is responsible for moving uploaded packages from the staging to rejected storage bucket in the event the file fails validation. It will also advertise successful payloads to the platform via the `platform.upload.available` topic. It reads from the `platform.upload.validation` topic by default.

## How it Works

![UML](http://www.plantuml.com/plantuml/png/hLAxRjmm4Epr5GlMbWzvL48W6EbI94tQ0C8UjISpvaFXBXKSZFnxI4idMxX74KG50N5dPdU6-y22KPApyCMp6Hw5uRk4Y0F1vnYUA5PZhXjjHlG24rhJenW_T4nnCfegycBa2AD5EOJekZJQW7rtGWQ_4U1PkzlFsbV8EA6nkBTKPGdS8rCclj2IVY9vlOtqaxIShi-dgzlhSpN0IMjYtXrojnG9NFx9NIgqCjUeXpS-87_VWX34aXE4muKu6dXMaNubOkbChnfGkDTz_UxzXu_gxeTNhtAbjWoW_XJj6n7MxJQtTVHrvCBVOkhsQgeDO3zH5CFaoByuMMimuh6WBxYzeVVyAMIOyMZ1yG0wUCd2xHse56rn-YWoShFRuM--dr_hFbUoSR9CK1xWF6l_NxDU7laVibwODxD-kvvDzZyUy-4S-aj1Ri7gQvY8Jxc3X6MhOGQe8h2XrErcxPkLMjfMb5i-v2Cv-nS0 "Insights Storage Broker")

Insights Storage Broker consumes from the `platform.upload.validation` topic. If the payload has succeeded validation, the storage broker will pass the message along with a download url to the `platform.upload.available` topic so that other services on the platform can consume it.

If a failure message is recieved, Storage Broker will copy the file to the rejected bucket and not advertise the availability of the payload to the platform.

## Authors

Stephen Adams - Initial Work - [SteveHNH](https://www.github.com/SteveHNH)