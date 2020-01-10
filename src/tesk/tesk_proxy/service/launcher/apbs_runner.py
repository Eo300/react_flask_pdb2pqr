import string, sys, os, time, errno, shutil, tempfile, urllib, copy, pickle, glob
import subprocess
from multiprocessing import Process

from requests import get, post
from json import loads

# from tmp_task_exec import executor_utils
from service import tesk_proxy_utils
from service.legacy.apbs_old_utils import fieldStorageToDict, pqrFileCreator, redirector

from service.legacy.src.aconf import INSTALLDIR, TMPDIR, APBS_LOCATION
from service.legacy.src.utilities import (getTrackingScriptString, 
                                                getEventTrackingString,
                                                startLogFile,
                                                resetLogFile)

def download_file(job_id, file_name, dest_path, storage_host):
    try:

        object_name = '%s/%s' % (job_id, file_name)
        response = get('%s/api/storage/%s/%s?json=true' % (storage_host, job_id, file_name))
        object_str = loads(response.content)[object_name]
        with open(dest_path, 'w') as fout:
            fout.write(object_str)
    except Exception as e:
        print('ERROR: %s'%e)

class JobDirectoryExistsError(Exception):
    def __init__(self, expression):
        self.expression = expression

class Runner:
    def __init__(self, storage_host, job_id=None, form=None, infile_name=None):
        self.job_id = None
        self.form = None
        self.infile_name = None
        self.read_file_list = []
        # self.read_file_list = None


        if infile_name is not None:
            self.infile_name = infile_name
        elif form is not None:
            self.form = form
            self.apbsOptions = fieldStorageToDict(form)

        if job_id is not None:
            self.job_id = job_id
        else:
            self.job_id = form['pdb2pqrid']

        self.job_dir = '%s%s%s' % (INSTALLDIR, TMPDIR, self.job_id)
        print(self.job_dir)
        if not os.path.isdir(self.job_dir):
            os.mkdir(self.job_dir)

    def prepare_job(self, storage_host):
        # taken from mainInput()
        print('preparing job execution')
        infile_name = self.infile_name
        form = self.form
        job_id = self.job_id

        # downloading necessary files
        if infile_name is not None:
            file_list = tesk_proxy_utils.apbs_extract_input_files(job_id, infile_name, storage_host)

            infile_dest_path = os.path.join(self.job_dir, infile_name)
            print('downloading infile')
            download_file(job_id, infile_name, infile_dest_path, storage_host)


            # print('parsing infile READ section')
            # file_list = []
            # with open(infile_dest_path, 'r') as fin:
            #     READ_start = False
            #     READ_end = False
            #     for whole_line in fin:
            #         line = whole_line.strip()
            #         for arg in line.split():
            #             # print(line.split())
            #             if arg.upper() == 'READ':
            #                 READ_start = True
            #             elif arg.upper() == 'END':
            #                 READ_end = True
            #             else:
            #                 file_list.append(arg)

            #             if READ_start and READ_end:
            #                 break
            #         if READ_start and READ_end:
            #             break
            # # removes the type of file/format from list (e.g. 'charge pqr')
            # print(file_list)
            # file_list = file_list[2:]
            # self.read_file_list = file_list
            print(file_list)
            # raise Exception('GONNA jump ship here')

            print('-----downloading other files-----')
            for name in file_list:
                dest_path = os.path.join(self.job_dir, name)
                download_file(job_id, name, dest_path, storage_host)
            print('---------------------------------')

            # download_file(job_id, infile_name, os.path.join(self.job_dir, infile_name), storage_host)

        elif form is not None:
            # tempPage = "results.html"   

            # apbsOptions = fieldStorageToDict(form)
            apbsOptions = self.apbsOptions

            # Extracts PQR file name from the '*.in' file within storage bucket
            pqrFileName = tesk_proxy_utils.apbs_extract_input_files(self.job_id, self.job_id+'.in', storage_host)[0]
            apbsOptions['pqrFileName'] = pqrFileName

            pqrFileCreator(apbsOptions)

            aoFile = open('%s%s%s/%s-ao' % (INSTALLDIR, TMPDIR, job_id, job_id),'w')
            pickle.dump(apbsOptions, aoFile)
            aoFile.close()


            # taken from apbsExec()

            # Copies PQR file to temporary directory
            # pqrFileName = form["pdb2pqrid"] + '.pqr'
            #shutil.copyfile('../pdb2pqr/tmp/%s' % pqrFileName, './tmp/%s/%s' % (job_id, pqrFileName))
            
            # Removes water from molecule if requested by the user
            try:
                if form["removewater"] == "on":
                    cur_dir = os.getcwd()
                    os.chdir('%stmp/%s' % (INSTALLDIR, job_id))
                    # os.chdir('./tmp/%s' % job_id)
                    inpath = pqrFileName 
                    print(os.getcwd())
                    infile = open(inpath, "r")
                    outpath = inpath[:-4] + '-nowater' + inpath[-4:]
                    outfile = open(outpath, "w")
                    newinpath = inpath[:-4] + '-water' + inpath[-4:]
                    newoutpath = inpath

                    while 1:
                        line = infile.readline()
                        if line == '':
                            break
                        if "WAT" in line:
                            pass
                        elif "HOH" in line:
                            pass
                        else:
                            outfile.write(line)
                    infile.close()
                    outfile.close()

                    shutil.move(inpath, newinpath)
                    shutil.move(outpath, newoutpath)
                    # os.chdir('../../')
                    os.chdir(cur_dir)

            except KeyError:
                pass

    def run_job(self, storage_host, tesk_host):
        job_id = self.job_id
        if self.infile_name is not None:
            infile_name = self.infile_name
        else:
            infile_name = 'apbsinput.in'

        
        # Write the start time to a file, before posting to TESK
        with open(os.path.join(INSTALLDIR, TMPDIR, job_id, 'apbs_start_time'), 'w') as fout:
            fout.write( str(time.time()) )

        # set the APBS status to running, write to disk, upload
        with open(os.path.join(INSTALLDIR, TMPDIR, job_id, 'apbs_status'), 'w') as fout:
            fout.write('running\n')
        print('infile name is: '+infile_name)
        upload_list = ['apbs_status', 'apbs_start_time', infile_name]
        tesk_proxy_utils.send_to_storage_service(storage_host, job_id, upload_list, os.path.join(INSTALLDIR, TMPDIR))

        # TESK request headers
        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        apbs_json = tesk_proxy_utils.apbs_json_config(job_id, infile_name, storage_host, os.path.join(INSTALLDIR, TMPDIR))

        from pprint import pprint
        pprint(apbs_json)

        url = tesk_host + '/v1/tasks'
        
        #TODO: create handler in case of non-200 response
        response = post(url, headers=headers, json=apbs_json)
        print(response.content)
        return

    def start(self, storage_host, tesk_host):
        # pass
        job_id = self.job_id


        # Prepare job
        self.prepare_job(storage_host)

        # Run PDB2PQR in separate process
        startLogFile(job_id, 'apbs_status', "running\n")

        print('Starting subprocess')
        # p = Process(target=self.run_job, args=(storage_host,))
        # p.start()

        self.run_job(storage_host, tesk_host)

        print('Getting redirector')
        redirect = redirector(job_id)

        # Upload initial files to storage service
        # file_list = [
        #     'apbs_status',
        #     'apbs_start_time',
        # ]
        # if isinstance(file_list, list):
        #     tesk_proxy_utils.send_to_storage_service(storage_host, job_id, file_list, os.path.join(INSTALLDIR, TMPDIR))

            # try:
            #     jobutils.send_to_storage_service(storage_host, job_id, file_list, os.path.join(INSTALLDIR, TMPDIR))
            # except Exception as err:
            #     sys.stderr.write(err)
            #     with open('storage_err', 'a+') as fin:
            #         fin.write(err)

        return redirect