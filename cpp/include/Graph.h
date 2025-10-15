#pragma once

// === Standard Library Includes ===
#include <algorithm>
#include <chrono>
#include <ctime>
#include <deque>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// === External Dependencies ===
#include "json.hpp"
using json = nlohmann::json;

// === Edge Structure ===
struct Edge {
    int source;
    int destination;
    double weight;          // -log(price) for Bellman-Ford
    double price;           // actual exchange rate
    std::string exchange;   // "Binance", "OKX", "Cross"
    std::string symbol;     // trading pair symbol
};

// === Graph Class ===
class Graph {
private:
    // === Core Graph Data ===
    std::unordered_map<std::string, int> nodeIds;  // node name -> ID mapping
    std::vector<std::string> nodeNames;            // ID -> node name mapping
    std::vector<Edge> edges;                       // all graph edges

    // === Cycle Deduplication ===
    std::deque<std::string> recentCycles;          // LRU cache of cycle signatures
    std::unordered_set<std::string> recentSet;     // fast lookup for duplicates
    static const size_t MAX_CYCLE_CACHE = 100;     // max cached cycles

    // === Profit Bucketing (unused, reserved for future) ===
    struct ArbitrageBucket {
        double representativeProfit;
        std::vector<std::string> cycles;
    };
    std::vector<ArbitrageBucket> profitBuckets;
    static constexpr double EPS_BUCKET = 1e-6;

    // === Super-Source Algorithm Support ===
    int superSourceId = -1;                        // super-source node ID
    size_t lastSuperEdgeAddForNodeCount = 0;       // track when to add new edges

    // === Helper Functions ===
    void ensureSuperSourceEdges();                 // create/update super-source connections
    bool warmupActive();                           // check if in warmup period

public:
    // === Graph Construction ===
    int addNode(std::string name);
    double addOrUpdateEdge(std::string source, 
                           std::string destination,
                           double price,
                           const std::string& exchange = "",
                           const std::string& symbol = "");

    // === Data Processing ===
    void processMessage(std::string msg);          // parse and add edge from JSON

    // === Arbitrage Detection ===
    void findArbitrage();                          // classic multi-source Bellman-Ford
    void findArbitrageSuperSource();               // super-source single-run Bellman-Ford

    // === Cycle Utilities ===
    std::vector<int> canonicalizeCycle(const std::vector<int>& cycle) const;
    std::string canonicalSignature(const std::vector<int>& cycle, double profit);
    std::string makeCycleSignature(const std::vector<int>& cycle, double profit);
    bool isDuplicateCycle(const std::string& sig);

    // === Bucketing (unused) ===
    int findExistingBucket(double profit);
    void printBucketSummary();

    // === Diagnostics ===
    void printAllEdges();
    void printGraphSummary(int maxEdgesToShow);
};