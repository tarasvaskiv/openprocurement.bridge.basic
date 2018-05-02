FROM python:3.6.5-stretch
RUN useradd api
RUN pip install virtualenv

WORKDIR /home/api
RUN chown -R api:api /home/api
USER api
ADD . .

RUN bash bootstrap.sh
RUN bin/buildout -N -c docker.cfg
ENTRYPOINT [ "bin/databridge" ]
CMD ["--help"]
