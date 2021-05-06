#!/usr/bin/env bash

java -Ddw.graphhopper.datareader.file=berlin-latest.osm.pbf -jar *.jar server config-example.yml
