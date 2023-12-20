# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  # Determine available host resources
  mem_ratio = 1.0/2
  cpu_exec_cap = 75
  host = RbConfig::CONFIG['host_os']
  # Give VM 1/2 system memory & access to all cpu cores on the host
  if host =~ /darwin/
    cpus = `sysctl -n hw.ncpu`.to_i
    # sysctl returns Bytes and we need to convert to MB
    mem = `sysctl -n hw.memsize`.to_i / (1024^2) * mem_ratio
  elsif host =~ /linux/
    cpus = `nproc`.to_i
    # meminfo shows KB and we need to convert to MB
    mem = `grep 'MemTotal' /proc/meminfo | sed -e 's/MemTotal://' -e 's/ kB//'`.to_i / 1024 * mem_ratio
  else # Windows folks
    cpus = `wmic cpu get NumberOfCores`.split("\n")[2].to_i
    mem = `wmic OS get TotalVisibleMemorySize`.split("\n")[2].to_i / 1024 * mem_ratio
  end
  config.vm.boot_timeout = 1800
  # Provision the "GradeScopeAutoGrader"
  config.vm.define :gsag do |gsag|
    gsag.vm.box = "ubuntu/focal64"
    gsag.vm.hostname = "gsag"
    gsag.vm.synced_folder ".", "/autograder/source", disabled: false
    gsag.ssh.forward_agent = true
    gsag.ssh.forward_x11 = true

    if mem < 2048
      puts "Your machine might not have enough memory to run this VM! Talk to the course staff."
    end

    gsag.vm.provider "virtualbox" do |vb|
      vb.customize ["modifyvm", :id, "--cpuexecutioncap", 75]
      vb.customize ["modifyvm", :id, "--memory", "2048"]
      vb.customize ["modifyvm", :id, "--cpus", "2"]
    end
    gsag.vm.provision "shell", inline: <<-'SHELL'
      sed -i 's/^#* *\(PermitRootLogin\)\(.*\)$/\1 yes/' /etc/ssh/sshd_config
      sed -i 's/^#* *\(PasswordAuthentication\)\(.*\)$/\1 yes/' /etc/ssh/sshd_config
      systemctl restart sshd.service
      echo -e "vagrant\nvagrant" | (passwd vagrant)
      echo -e "root\nroot" | (passwd root)
    SHELL
    gsag.vm.provision "shell", path: "setup.sh", privileged: true

  end

end

