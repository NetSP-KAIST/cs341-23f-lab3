cd /autograder/

# Copy run_autograder to /autograder
cp /autograder/source/run_autograder /autograder/

# run setup.sh
sudo /autograder/source/setup.sh

# Make results, submission folder look like gradescope autograder
mkdir /autograder/results
touch /autograder/results/stdout
mkdir /autograder/submission
cp /autograder/task_*.py /autograder/submission/