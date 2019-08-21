# Insights Storage Broker

The Insights Storage Broker microservice is responsible for moving uploaded packages from the staging to rejected storage bucket in the event the file fails validation. It reads from the `platform.ingress.reject` topic by default.

## How it Works

![UML](http://www.plantuml.com/plantuml/png/TL1BReCm4Dtx52ElowAV5GkK2xGdg8G6Uw1k_A7Z0GbLlNjDapIbA1kGthpFypjaGPOfU3MMlpDkn2WmetSMnSMXpSIpCwGeYfC5He_I9mvjkJ7bt3Azav6DEajY7AZjE1s9LJ723ZCL_0UTp97aYfuCBl0-kMfkPDRGe_CJ4uG25clraeI0tV0ca7hOMzNmgPa-9ihIEgjhqDWPMzq_F3xfkzUeBueKrzlPNN-f6mMgPllIVQ7jVULV5wZ1f74fdn0msd_TjqJzd6RACEBY4rgGT1uDJWIj_jAhPhDe_IjRuzI1efs2_mO0 "Insights Storage Broker")

Insights Storage Broker consumes from the `platform.ingress.reject` topic. It takes the key in the message and passed it to a copy command that moves the file from one bucket to the other

## Authors

Stephen Adams - Initial Work - [SteveHNH](https://www.github.com/SteveHNH)