#!/bin/bash
## Install Go version 16.4
SKIP=false
# check if Go is already installed
echo "Starting Go 1.16.4 installation"
if echo $PATH | grep -q "go"
then
    echo "Go already installed. Checking version"  # TODO check Go version > 1.16
    if go version | grep -Eq "go1.1[6-9]"
    then
        echo "Installed version meets requirements. Skipping Go installation"
        SKIP=true
    fi
fi

if [[ $SKIP = false ]]
then
    # create ~/src directory
    echo "Creating $HOME/src directory"
    mkdir $HOME/src

    # match everything after NAME="..." - find os type to fetch correct file from golang server
    echo "Checking platform"
    OS_NAME=$(cat /etc/*-release | grep -w NAME= | sed 's/NAME=//g' | sed 's/\"//g')
    echo $OS_NAME
    PLATFORM=""
    if [[ $OS_NAME == "Ubuntu" ]]
    then
        PLATFORM="amd64"
    fi 

    # TODO: check if correct on RPI 3 and 4
    if [[ $OS_NAME == "Raspbian GNU/Linux" ]]
    then
        PLATFORM="armv6l"
    fi

    echo "Found $PLATFORM"
    FILENAME="go1.16.4.linux-"$PLATFORM".tar.gz"
    echo $FILENAME.tar.gz
    URL="https://dl.google.com/go/go1.16.4.linux-"$PLATFORM".tar.gz"

    # download archive
    echo "Downloading Go from $URL"
    wget -P ~/src $URL

    # extract the package
    sudo tar -C /usr/local -xzf "$HOME/src/"$FILENAME
    rm "$HOME/src/"$FILENAME

    # configure Go
    if cat ~/.bashrc | grep -Fq "PATH=\$PATH:/usr/local/go/bin"
    then
        echo "Go executable already on \$PATH"
    else
        echo "Go executable not on \$PATH yet. Adding to ~/.bashrc"
        echo "export PATH=\$PATH:/usr/local/go/bin" >> ~/.bashrc
    fi

    if cat ~/.bashrc | grep -Fq "GOPATH=$HOME/go"
    then
        echo "GOPATH already set"
    else
        echo "GOPATH not set yet. Adding to ~/.bashrc"
        echo "export GOPATH=$HOME/go" >> ~/.bashrc
    fi
fi

## Install mcumgr
if cat ~/.bashrc | grep -Fq "mcumgr"
then
    echo "mcumgr already on \$PATH"
    else
    mkdir -p $GOPATH/src/mynewt.apache.org/

    echo "Cloning mcumgr CLI tool"
    cd $HOME/src && git clone https://github.com/apache/mynewt-mcumgr-cli.git && mv mynewt-mcumgr-cli $GOPATH/src/mynewt.apache.org/mcumgr
    echo "Installing mcumgr CLI tool"
    cd $GOPATH/src/mynewt.apache.org/mcumgr/mcumgr && go build
    echo "mcumgr not on \$PATH yet. Adding to. Adding to ~/.bashrc"
    echo "export PATH=\$PATH:$GOPATH/src/mynewt.apache.org/mcumgr/mcumgr" >> ~/.bashrc
fi

# update shell with changes
source ~/.bashrc