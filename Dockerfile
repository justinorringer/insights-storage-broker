FROM registry.redhat.io/ubi8/python-36
COPY src src
COPY setup.py .
COPY default_map.yaml .
RUN pip3 install .
USER 0
RUN yum remove -y npm nodejs kernel-headers
USER 1001
ENTRYPOINT ["storage_broker"]