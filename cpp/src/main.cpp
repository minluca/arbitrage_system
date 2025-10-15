#include "SocketClient.hpp"
#include "Graph.h"
#include <iostream>
#include <limits>

int main() {
    std::cout << "=== Sistema di Rilevamento Arbitraggio ===\n";
    std::cout << "1. Modalità classica (Bellman-Ford da tutte le sorgenti)\n";
    std::cout << "2. Modalità super-sorgente unica\n";
    std::cout << "Scelta: ";

    int mode = 0;
    while (true) {
        std::cin >> mode;
        if (std::cin.fail() || (mode != 1 && mode != 2)) {
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            std::cout << "Scelta non valida. Inserisci 1 o 2: ";
        } else break;
    }
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

    Socket::Client client("127.0.0.1", 5001);
    Graph g;

    std::cout << "\n[INFO] Modalità selezionata: "
              << (mode == 1 ? "Classica" : "Super-sorgente")
              << "\n[INFO] Attendo dati dal server Python...\n"
              << "--------------------------------------------\n";

    while (true) {
        std::string msg = client.receiveMessage();
        g.processMessage(msg);
        
        if (mode == 1)
            g.findArbitrage();
        else
            g.findArbitrageSuperSource();
    }

    return 0;
}