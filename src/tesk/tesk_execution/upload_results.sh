#!/bin/sh

# for file in _upload/*
cur_dir=$(pwd)
task_name=$1

mkdir _upload
cp * _upload

cd ./_upload

ls

rm ${task_name}_status

if [ ${task_name} = 'pdb2pqr' ]
then
  cp *.in apbsinput.in

  pdb_name=$(ls *.pdb)
  userff_name=$(ls *.DAT)
  usernames_name=$(ls *.names)
  ligand_name=$(ls *.mol2)

  output_basename=$2

  echo ''
  echo 'Writing pdb2pqr_status'

  # Write to the pdb2pqr_status
  echo 'complete'        >> ${task_name}_status
  
  # Write the PDB input file
  if [ $pdb_name != '' ]
  then
    echo $JOB_ID/$pdb_name >> ${task_name}_status
  fi

  # Write the User Forcefield input file
  if [ $userff_name != '' ]
  then
    echo $JOB_ID/$userff_name >> ${task_name}_status
  fi
  
  # Write the User Names input file
  if [ $usernames_name != '' ]
  then
    echo $JOB_ID/$usernames_name >> ${task_name}_status
  fi

  # Write the Ligand input file
  if [ $ligand_name != '' ]
  then
    echo $JOB_ID/$ligand_name >> ${task_name}_status
  fi

  # Write the output files
  for file in $output_basename*
  do
    echo $JOB_ID/${file} >> ${task_name}_status
  done
  
elif [ ${task_name} = 'apbs' ]
then
  pqr_name=$(ls *.pqr)
  # dx_name=*.dx
  echo ''
  echo 'Writing apbs_status'

  echo 'complete'           >> ${task_name}_status
  echo $JOB_ID/apbsinput.in >> ${task_name}_status
  echo $JOB_ID/$pqr_name    >> ${task_name}_status
  echo $JOB_ID/io.mc        >> ${task_name}_status
  
  for file in *.dx
  do
    echo $JOB_ID/${file} >> ${task_name}_status
  done

  echo $JOB_ID/apbs_stdout.txt >> ${task_name}_status
  echo $JOB_ID/apbs_stderr.txt >> ${task_name}_status
fi

# for file in *
# do
#   # echo "curl -v -F file_data=@${file} $STORAGE_HOST/api/storage/$JOB_ID/${file}"
#   echo $JOB_ID/${file} >> $1_status
# done

for file in *
do
  # echo "curl -v -F file_data=@${file} $STORAGE_HOST/api/storage/$JOB_ID/${file}"
  curl -v -F file_data=@${file} $STORAGE_HOST/api/storage/$JOB_ID/${file}
done

cd $cur_dir