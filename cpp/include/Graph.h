#pragma once

#include <unordered_map>
#include <string>
#include <vector>
#include <iostream>
#include <sstream>
// lib header only di Lohmann per manipolare JSON
#include "json.hpp"
using json = nlohmann::json;
#include <limits>
#include <chrono>
#include <iomanip>
#include <ctime>
#include <deque>
#include <set>
#include <unordered_set>
#include <algorithm>

struct Edge {
    int source;
    int destination;
    double weight;          // -log(price)
    double price;           // prezzo reale
    std::string exchange;   // "Binance" / "OKX" / "Cross"
    std::string symbol;     // coppia o simbolo originale
};

class Graph{
    private:
        std::unordered_map<std::string, int> nodeIds;
        std::vector<std::string> nodeNames;
        std::vector<Edge> edges;
        std::deque<std::string> recentCycles;
        std::unordered_set<std::string> recentSet;
        static const size_t MAX_CYCLE_CACHE = 100;

        // --- Gestione bucket di arbitraggi analoghi ---
        struct ArbitrageBucket {
            double representativeProfit;
            std::vector<std::string> cycles;  // sig o path testuale
        };

        std::vector<ArbitrageBucket> profitBuckets;
        static constexpr double EPS_BUCKET = 1e-6;  // tolleranza per considerare due profitti identici
    public:
        int addNode(std::string name);
        double addOrUpdateEdge(std::string source, std::string destination,
                       double price,
                       const std::string& exchange = "",
                       const std::string& symbol = "");
        void printAllEdges();
        void processMessage(std::string msg);
        void findArbitrage();
        void printGraphSummary(int maxEdgesToShow);
        std::string makeCycleSignature(const std::vector<int>& cycle, double profit);
        bool isDuplicateCycle(const std::string& sig);
        std::vector<int> canonicalizeCycle(const std::vector<int>& cycle) const;
        std::string canonicalSignature(const std::vector<int>& cycle, double profit);
        int findExistingBucket(double profit);
        void printBucketSummary();
};