#include "SocketClient.hpp"
#include "Graph.h"
#include <iostream>

int main() {
    Socket::Client client("127.0.0.1", 5001);
    Graph g;

    int counter = 0;

    while (true) {
        std::string msg = client.receiveMessage();
        g.processMessage(msg);
        
        g.findArbitrage();

        // counter++;
        // if (counter % 1000 == 0) {
        //     std::cout << "\n[DEBUG] Stampa grafo dopo " << counter << " messaggi" << std::endl;
        //     g.printGraphSummary(150);
        // }
    }

    return 0;
}