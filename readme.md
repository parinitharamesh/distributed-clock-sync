# Distributed Clock Synchronization System using UDP

## Description
This project implements a distributed clock synchronization system using UDP socket programming. A central server communicates with multiple clients to synchronize their clocks based on calculated network delay and clock offset.

The system also includes encryption and a basic reliability mechanism to improve security and accuracy.

## Components
- **server.py** – Handles client requests, computes timestamps, and maintains statistics  
- **client.py** – Sends synchronization requests and adjusts its clock  
- **server_ui.html** – Displays server-side monitoring dashboard  
- **client_ui.html** – Displays client-side synchronization details  

## How to Run

### 1. Run the Server
   python server.py

### 2. Run the Client
   python client.py

- Enter a unique **Client ID**
- Open the UI files in a browser

## Features
- UDP socket communication  
- Clock synchronization using timestamp exchange  
- Network delay and clock offset calculation  
- Encrypted communication (Fernet - AES)  
- Stop-and-Wait ARQ for reliability  
- Multi-client support  
- Real-time monitoring dashboards  

## Performance Results
- Average delay: **0.001 – 0.002 seconds**  
- Multiple clients tested successfully  
- Reliable synchronization achieved  

## Limitations
- UDP does not guarantee delivery  
- Best suited for local networks  
- Single server system  

## Future Improvements
- Multi-server synchronization  
- Graph-based visualization  
- Deployment over larger networks  
