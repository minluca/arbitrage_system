#include "SocketClient.hpp"
#include "Graph.h"
#include <iostream>
#include <limits>
#include <thread>
#include <filesystem>

int main() {
    std::cout << "=== Arbitrage Detection System ===\n";
    std::cout << "1. All sources\n";
    std::cout << "2. Single source\n";
    std::cout << "3. Benchmark (performance comparison)\n";
    std::cout << "Choice: ";
    
    int mode = 0;
    while (true) {
        std::cin >> mode;
        if (std::cin.fail() || (mode < 1 || mode > 3)) {
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            std::cout << "Invalid choice. Enter 1, 2 or 3: ";
        } else break;
    }
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    
    Socket::Client client("127.0.0.1", 5001);
    Graph g;
    
    if (mode == 1) {
        std::cout << "\n[INFO] Selected mode: Classic\n";
        
        auto now = std::chrono::system_clock::now();
        auto timestamp = std::chrono::system_clock::to_time_t(now);
        std::tm tm = *std::localtime(&timestamp);
        
        std::ostringstream filename;
        filename << "arbitrage_results_"
                 << std::put_time(&tm, "%Y%m%d_%H%M%S")
                 << ".csv";
        
        g.enableCSVLogging(filename.str());
    }
    else if (mode == 2) {
        std::cout << "\n[INFO] Selected mode: Super-source\n";
    }
    else {
        std::cout << "\n[INFO] Selected mode: Benchmark\n";
    }
    
    std::cout << "[INFO] Waiting for data from Python server...\n"
              << "--------------------------------------------\n";
    
    while (true) {
        std::string msg = client.receiveMessage();
        g.processMessage(msg);
        
        if (mode == 1)
            g.findArbitrage();
        else if (mode == 2)
            g.findArbitrageSuperSource();
        else
            g.runBenchmark();
    }
    
    return 0;
}