#!/bin/bash

if [ "$1" = "download" ]; then
    echo "----------------------------------------"
    echo "Downloading SRTM data...";
    echo "----------------------------------------"
    curl -o /SRTM/M31.zip \
         -o /SRTM/L31.zip \
         -o /SRTM/K31.zip \
         -o /SRTM/M32.zip \
         -o /SRTM/L32.zip \
         -o /SRTM/K32.zip \
         -o /SRTM/M33.zip \
         -o /SRTM/L33.zip \
         -o /SRTM/K33.zip \
    https://viewfinderpanoramas.org/dem1/M31.zip \
    https://viewfinderpanoramas.org/dem1/L31.zip \
    https://viewfinderpanoramas.org/dem1/K31.zip \
    https://viewfinderpanoramas.org/dem1/M32.zip \
    https://viewfinderpanoramas.org/dem1/L32.zip \
    https://viewfinderpanoramas.org/dem1/K32.zip \
    https://viewfinderpanoramas.org/dem1/M33.zip \
    https://viewfinderpanoramas.org/dem1/L33.zip \
    https://viewfinderpanoramas.org/dem1/K33.zip

    echo "----------------------------------------"
    echo "Unzip downloaded SRTM files..."
    echo "----------------------------------------"
    cd /SRTM
    for file in *.zip; do unzip -j "$file" -d /SRTM; done

    echo "----------------------------------------"
    echo "Convert *.hgt files to *-hd.srt files..."
    echo "----------------------------------------"
    shopt -s nullglob; for f in /SRTM/*.hgt; do echo "Converting $f"; srtm2sdf-hd "$f"; done

    echo "----------------------------------------"
    echo "Done!"
    echo "----------------------------------------"
fi
