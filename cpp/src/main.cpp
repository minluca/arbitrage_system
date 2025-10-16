#include "SocketClient.hpp"
#include "Graph.h"
#include <iostream>
#include <limits>

int main() {
    std::cout << "=== Sistema di Rilevamento Arbitraggio ===\n";
    std::cout << "1. Tutte le sorgenti\n";
    std::cout << "2. Sorgente unica\n";
    std::cout << "3. Benchmark (confronto performance)\n";
    std::cout << "Scelta: ";

    int mode = 0;
    while (true) {
        std::cin >> mode;
        if (std::cin.fail() || (mode < 1 || mode > 3)) {
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            std::cout << "Scelta non valida. Inserisci 1, 2 o 3: ";
        } else break;
    }
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

    Socket::Client client("127.0.0.1", 5001);
    Graph g;

    std::cout << "\n[INFO] Modalità selezionata: ";
    if (mode == 1) std::cout << "Classica\n";
    else if (mode == 2) std::cout << "Super-sorgente\n";
    else std::cout << "Benchmark\n";
    
    std::cout << "[INFO] Attendo dati dal server Python...\n"
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