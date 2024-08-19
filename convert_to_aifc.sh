#!/usr/bin/env bash

if [[ -z $1 ]]; then
    echo 'Usage: <wav filename> <aifc filename> [-o order] [-t table size] [-f frame size] [-r refine iterations]'
    exit 1
fi

input=$1
output=$2
order=2
table=2
frame=16
refine=1000

infile=$(basename "${input}" .wav)


while getopts o:t:f:r: flag
do
    case "${flag}" in
        o) order=${OPTARG};;
        t) table=${OPTARG};;
        f) frame=${OPTARG};;
        r) refine=${OPTARG};;
    esac
done

tools/z64audio/z64audio -i "${input}" -o "/tmp/${infile}.aiff" -b -m
tools/tabledesign -o ${order} -i ${refine} -s ${table} -f ${frame} "/tmp/${infile}.aiff" > "/tmp/${infile}.aif.tbl"
tools/vadpcm_enc -c "/tmp/${infile}.aif.tbl" "/tmp/${infile}.aiff" "${output}"
rm -f "/tmp/${infile}.aif.tbl" "/tmp/${infile}.aiff"
