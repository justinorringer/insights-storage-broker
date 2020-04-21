FROM registry.redhat.io/ubi8/python-36
COPY src src
COPY setup.py .
COPY default_map.yaml .
RUN pip3 install .
ENTRYPOINT ["storage_broker"]