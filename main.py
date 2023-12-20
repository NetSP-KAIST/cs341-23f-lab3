from os import listdir, walk
from subprocess import run
from os.path import join
from time import sleep
import argparse

import paramiko
import yaml
import pyperclip
import tqdm

testCount = 10

sshconfig = {
    'HostName': None,
    'User': None,
    'Port': None,
    'IdentityFile': None
}

def parseSSHConfig():
    global sshconfig
    p = run('vagrant ssh-config', shell=True, text=True, capture_output=True)
    for line in p.stdout.splitlines():
        ls = line.strip().split()
        try:
            if ls[0] in sshconfig.keys():
                sshconfig[ls[0]] = ls[1]
        except:
            pass
    for v in sshconfig.values():
        if v is None:
            raise Exception('Failed to parse vagrant ssh-config')
        
class PS:
    def __init__(self, cmd):
        # open SSH session for executing command; POX only allows this
        import paramiko
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=sshconfig['HostName'], port=sshconfig['Port'], username=sshconfig['User'], key_filename=sshconfig['IdentityFile'])
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command('cd /autograder;'+cmd, get_pty=True)
    def readlines(self):
        lines = self.stdout.readlines()
        if len(lines) == 0:
            print(self.stderr.readlines())
        self.ssh.close()
        return lines
    def kill(self):
        # 0 (stop receiving), 1 (stop sending), 2 (stop receiving and sending).
        self.ssh.close()
    def wait(self):
        self.stdout.readlines()
        self.ssh.close()


def gradeTask(task=1):
    poxps = None
    if task > 1:
        poxps = PS('sudo pox/pox.py misc.controller')
        sleep(5)
    gradeps = PS('sudo ./grade.py --task {}'.format(task))
    output = gradeps.readlines()
    if poxps:
        # sometimes pox does not accept SIGINT... IDK why
        PS('sudo pkill -2 -f pox').wait()
        PS('sudo pkill -2 -f pox').wait()
        PS('sudo pkill -2 -f pox').wait()
        poxps.wait()
    return output

def cleanup():
    PS('sudo rm submission/task_*.py').wait()
    PS('sudo rm task_*.py').wait()
    PS('sudo pkill -f pox; sudo pkill ovs-vswit').wait()
    mininetstop = PS('sudo mn -c')
    sleep(3)
    # sometimes this hang
    PS('sudo pkill -2 -f mn').wait()
    mininetstop.wait()
    # do it again
    PS('sudo mn -c').wait()


class Submission:
    def __init__(self, id, submitter, path):
        self.id = id
        self.submitter = submitter
        self.path = path
        self.wrongFormat = False
        taskfiles = filter(lambda fn:fn in ['task_controller.py', 'task_topology.py'], listdir(path))
        self.files = list(map(lambda fn: join(path, fn), taskfiles))
        if len(self.files) < 2:
            taskfiles = []
            for (root, dirs, files) in walk(path):
                taskfiles.extend(filter(lambda fn:fn in ['task_controller.py', 'task_topology.py'], files))
            if len(taskfiles) > len(self.files):
                self.files = taskfiles
                self.wrongFormat = True

def get_submissions():
    # find assignment_*****_export folder
    assignment = list(filter(lambda fn: 'assignment' in fn, listdir()))[0]
    submissions = []
    with open(join(assignment, 'submission_metadata.yml'), encoding='utf-8') as f:
        metadata = yaml.load(f, Loader=yaml.FullLoader)
        for submissionID in sorted(metadata.keys()):
            submitters = metadata[submissionID][':submitters']
            if len(submitters) != 1:
                errormsg = 'metadata parsing error: more than 1 submitter in submission: {}'.format(submissionID)
                errormsg += '\nsubmitters: \n'
                errormsg += yaml.dump(submitters)
                raise Exception(errormsg)
            submissions.append(Submission(submissionID, submitters[0], join(assignment, submissionID)))

    return submissions

def main():
    parser = argparse.ArgumentParser(prog='CS341 SDN Lab Tester')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--idx', metavar='I', type=str, nargs='?', default='-',
                        help='submission idx to grade; ex) 5 / 2-4', required=False)
    args = parser.parse_args()
    debug = args.debug
    run('vagrant up', shell=True)
    parseSSHConfig()
    idx = 43 # which idx to start grading
    submissions = []
    if debug:
        # do same grading 10 times
        # upload task_*.py in the same folder
        idx = 0
        submissions = [Submission('debug', 'debug', './')]
    else:
        submissions = get_submissions()
    idx = args.idx
    idxsplit = idx.split('-')
    if len(idxsplit) == 1:
        # single number input
        idx = int(idx)
        submissions = [submissions[idx]]
    elif len(idxsplit) == 2:
        # range input (x-y)
        x,y = idxsplit
        if x == '':
            x = '0'
        if y == '':
            submissions = submissions[int(x):]
        else:
            submissions = submissions[int(x):int(y)]
        idx = int(x)
    else:
        raise Exception('Invalid index : {}'.format(idx))
    for submission in submissions:
        print('checking {}th submission'.format(idx+1))
        print('submitter: ')
        print(submission.submitter)
        idx += 1
        run('vagrant up', shell=True)
        ## Upload files to /autograder/submission/
        for filepath in submission.files:
            run('vagrant upload "{}"'.format(filepath), shell=True)
        PS('sudo mv ~/task_*.py /autograder/submission/').wait()

        PS('sudo cp submission/task_*.py ./').wait()
        total_output = ''
        
        grades = [0.0, 0.0, 0.0, 0.0]
        for i in tqdm.trange(testCount):
            output = gradeTask(1)
            try:
                grades[0] += float(output[-1].strip().split(':')[-1]) / testCount
            except:
                output += '\nGrade of task 1:0\n'
            total_output += ''.join(output)
        
        for i in tqdm.trange(testCount):
            output = gradeTask(3)
            try:
                grades[1] += float(output[-1].strip().split(':')[-1]) / testCount
            except:
                output += '\nGrade of task 3:0\n'
            total_output += ''.join(output)
        
        for i in tqdm.trange(testCount):
            output = gradeTask(4)
            try:
                grades[2] += float(output[-1].strip().split(':')[-1]) / testCount
            except:
                output += '\nGrade of task 4:0\n'
            total_output += ''.join(output)

        for i in tqdm.trange(testCount):
            output = gradeTask(5)
            try:
                grades[3] += float(output[-1].strip().split(':')[-1]) / testCount
            except:
                output += '\nGrade of task 5:0\n'
            total_output += ''.join(output)
        
        total_output += '\n\n'
        total_output += 'Submitter information: {}\n'.format(submission.submitter)
        total_output += 'Grade of task 1: {}\n'.format(grades[0])
        total_output += 'Grade of task 3: {}\n'.format(grades[1])
        total_output += 'Grade of task 4: {}\n'.format(grades[2])
        total_output += 'Grade of task 5: {}\n'.format(grades[3])
        totalgrade = sum(grades)
        if submission.wrongFormat:
            total_output += 'Wrong Format Penalty: 10%\n'
            totalgrade *= 0.9
        total_output += 'Total Grade: {}\n'.format(totalgrade)
        print('Grade: {}'.format(totalgrade))

        outputpath = join(submission.path, 'output_{}.txt'.format(submission.id))

        with open(outputpath,'a' if debug else 'w') as f:
            f.write(total_output)
            print('saved output to {}'.format(outputpath))
        cleanup()
        run('vagrant halt', shell=True)
if __name__ == '__main__':
    main()