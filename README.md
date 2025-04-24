**Required dependencies**

This project uses the cryptography library and we need to install it.


If you are on Ubuntu/Debian, you need to install the following dependencies first. If you are on macOS/Windows, skip ahead to the Installation section.

1. build-essential

2. libssl-dev 

3. libffi-dev

4. python3-dev 

5. cargo

6. pkg-config

To install the above dependencies:
```code
sudo apt-get install build-essential libssl-dev libffi-dev \
    python3-dev cargo pkg-config
```

**Installation**

Once dependencies are installed, run the command below.

```code
pip install cryptography
```

**How to run the code (INCOMPLETE)**

1. Run tracker.py

2. Run peer.py for each peer you want to create

3. Profit

**Assumptions Made**

1. Tracker does not go offline.