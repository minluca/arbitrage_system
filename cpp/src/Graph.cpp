#include "Graph.h"

static constexpr double PROFIT_MIN = 1.00005;
static constexpr int MIN_CYCLE_LEN = 3;

int Graph::addNode(std::string name)
{
    if (nodeIds.find(name) == nodeIds.end()) {
        int id = static_cast<int>(nodeNames.size());
        nodeIds[name] = id;
        nodeNames.push_back(name);
        return id;
    } else {
        return nodeIds[name];
    }
}

double Graph::addOrUpdateEdge(std::string s, std::string d, double p,
                              const std::string& exch,
                              const std::string& sym)
{
    if (!std::isfinite(p) || p <= 0.0) {
        std::cerr << "[warn] addOrUpdateEdge: prezzo non valido (p=" << p
                  << ") per " << s << "->" << d << " exch=" << exch << " sym=" << sym << "\n";
        return std::numeric_limits<double>::quiet_NaN();
    }
    
    if (exch == "Cross") {
        if (std::fabs(p - 1.0) > 1e-9) {
            std::cerr << "[error] addOrUpdateEdge: ponte cross-exchange con price != 1.0 (p=" << p
                      << ") per " << s << "->" << d << " - RIFIUTATO\n";
            return std::numeric_limits<double>::quiet_NaN();
        }
    } else {
        if (p < 1e-8 || p > 1e8) {
            std::cerr << "[error] addOrUpdateEdge: prezzo ESTREMO fuori range (p=" << p
                      << ") per " << s << "->" << d << " - RIFIUTATO\n";
            return std::numeric_limits<double>::quiet_NaN();
        }
                
        bool isStablePair = false;
        std::vector<std::string> stables = {"USDT", "USDC", "TUSD"};
        
        for (const auto& stable : stables) {
            if ((s.find(stable) != std::string::npos) && 
                (d.find(stable) != std::string::npos)) {
                isStablePair = true;
                break;
            }
        }
        
        if (isStablePair) {
            if (p < 0.99 || p > 1.01) {
                std::cerr << "[warn] addOrUpdateEdge: coppia stablecoin con price anomalo (p=" << p
                          << ") per " << s << "->" << d << " - potenziale errore dati\n";
            }
        }
    }

    int u = addNode(s);
    int v = addNode(d);

    double w = -std::log(p);
    if (!std::isfinite(w)) {
        std::cerr << "[warn] addOrUpdateEdge: peso non finito per p=" << p
                  << " su " << s << "->" << d << "\n";
        return std::numeric_limits<double>::quiet_NaN();
    }

    for (auto& e : edges) {
        if (e.source == u && e.destination == v) {
            e.weight = w;
            e.price  = p;
            if (!exch.empty()) e.exchange = exch;
            if (!sym.empty())  e.symbol   = sym;
            return w;
        }
    }

    Edge e{u, v, w, p, exch, sym};
    edges.push_back(e);
    
    if (exch != "Cross" && p > 0.0) {
        double p_inv = 1.0 / p;
        double w_inv = -std::log(p_inv);
        
        if (std::isfinite(w_inv)) {
            bool inverseExists = false;
            for (auto& edge : edges) {
                if (edge.source == v && edge.destination == u) {
                    edge.weight = w_inv;
                    edge.price = p_inv;
                    if (!exch.empty()) edge.exchange = exch;
                    if (!sym.empty()) edge.symbol = sym + "_INV";
                    inverseExists = true;
                    break;
                }
            }
            
            if (!inverseExists) {
                Edge e_inv{v, u, w_inv, p_inv, exch, sym + "_INV"};
                edges.push_back(e_inv);
            }
        }
    }
    
    return w;
}

void Graph::printAllEdges() {
    for (auto& e : edges) {
        std::cout << nodeNames[e.source] << " -> " << nodeNames[e.destination]
                  << " ha peso = " << e.weight << std::endl;
    }
}

void Graph::processMessage(std::string msg) {
    try {
        auto j = json::parse(msg);
        std::string base = j["base"];
        std::string quote = j["quote"];
        std::string exchange = j.value("exchange", "");
        std::string symbol = j.value("symbol", "");
        double price = j["price"];

        std::string source = base;
        std::string destination = quote;
        
        if (exchange != "Cross") {
            if (source.find("_Binance") == std::string::npos && 
                source.find("_OKX") == std::string::npos &&
                source.find("_Bybit") == std::string::npos) {
                source += "_" + exchange;
            }
            
            if (destination.find("_Binance") == std::string::npos && 
                destination.find("_OKX") == std::string::npos &&
                destination.find("_Bybit") == std::string::npos) {
                destination += "_" + exchange;
            }
        }

        addOrUpdateEdge(source, destination, price, exchange, symbol);
        
    } catch (std::exception& e) {
        std::cerr << "[Graph] Errore processMessage: " << e.what() << std::endl;
    }
}

std::string Graph::makeCycleSignature(const std::vector<int>& cycle, double profit) {
    std::set<std::string> uniqueNodes;
    for (int n : cycle) uniqueNodes.insert(nodeNames[n]);
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(4) << profit << "|";
    for (const auto& name : uniqueNodes) oss << name << ",";
    return oss.str();
}

bool Graph::isDuplicateCycle(const std::string& sig) {
    if (recentSet.find(sig) != recentSet.end()) {
        return true;
    }

    recentCycles.push_back(sig);
    recentSet.insert(sig);

    if (recentCycles.size() > MAX_CYCLE_CACHE) {
        recentSet.erase(recentCycles.front());
        recentCycles.pop_front();
    }

    return false;
}

std::vector<int> Graph::canonicalizeCycle(const std::vector<int>& cycle) const {
    if (cycle.empty()) return cycle;
    const int n = static_cast<int>(cycle.size());

    auto rotate_min = [&](const std::vector<int>& seq) {
        int m = 0;
        for (int i = 1; i < n; ++i)
            if (nodeNames[seq[i]] < nodeNames[seq[m]]) m = i;
        std::vector<int> rot(n);
        for (int i = 0; i < n; ++i) rot[i] = seq[(m + i) % n];
        return rot;
    };

    std::vector<int> fwd = rotate_min(cycle);
    std::vector<int> rev = cycle;
    std::reverse(rev.begin(), rev.end());
    rev = rotate_min(rev);

    for (int i = 0; i < n; ++i) {
        const std::string& a = nodeNames[fwd[i]];
        const std::string& b = nodeNames[rev[i]];
        if (a < b) return fwd;
        if (a > b) return rev;
    }
    return fwd;
}

std::string Graph::canonicalSignature(const std::vector<int>& cycle, double profit) {
    auto canon = canonicalizeCycle(cycle);
    std::ostringstream oss;
    
    for (size_t i = 0; i < canon.size(); ++i) {
        if (i) oss << "->";
        oss << nodeNames[canon[i]];
    }
    return oss.str();
}

int Graph::findExistingBucket(double profit) {
    for (int i = 0; i < (int)profitBuckets.size(); ++i)
        if (std::fabs(profitBuckets[i].representativeProfit - profit) < EPS_BUCKET)
            return i;
    return -1;
}

void Graph::findArbitrage() {
    const int V = static_cast<int>(nodeNames.size());
    if (V == 0) return;

    using clock_wall = std::chrono::system_clock;

    static bool warmupInitialized = false;
    static std::time_t startEpoch = 0;
    static std::time_t lastWarnedSec = -1;
    const int WARMUP_SECONDS = 3;

    std::time_t nowEpoch = std::chrono::system_clock::to_time_t(clock_wall::now());
    if (!warmupInitialized) {
        warmupInitialized = true;
        startEpoch = nowEpoch;
    }
    if (nowEpoch - startEpoch < WARMUP_SECONDS) {
        if (nowEpoch != lastWarnedSec) {
            std::tm tm = *std::localtime(&nowEpoch);
            std::cout << "[warm-up] Ignoro arbitraggio per altri "
                      << (WARMUP_SECONDS - (nowEpoch - startEpoch))
                      << "s @ " << std::put_time(&tm, "%H:%M:%S") << std::endl;
            lastWarnedSec = nowEpoch;
        }
        return;
    }

    static std::time_t lastSecond = 0;
    static int foundThisSecond = 0;

    std::time_t secNow = clock_wall::to_time_t(clock_wall::now());
    if (lastSecond == 0) lastSecond = secNow;
    
    if (secNow != lastSecond) {
        if (foundThisSecond == 0) {
            std::tm t = *std::localtime(&lastSecond);
            std::cout << "--- Nessun arbitraggio tra "
                      << std::put_time(&t, "%H:%M:%S") << " e "
                      << std::put_time(std::localtime(&secNow), "%H:%M:%S")
                      << " ---\n";
        } else {
            std::tm t = *std::localtime(&lastSecond);
            std::cout << "=== Arbitraggi trovati @ " << std::put_time(&t, "%H:%M:%S")
                      << " => " << foundThisSecond << " ===\n\n";
        }
        foundThisSecond = 0;
        lastSecond = secNow;
    }

    static constexpr double RELAX_EPS = 1e-6;
    static constexpr double PROFIT_MIN_LOCAL = 1.000001;
    static constexpr double PROFIT_MAX_LOCAL = 10.0;

    for (int start = 0; start < V; ++start) {
        std::vector<double> dist(V, std::numeric_limits<double>::infinity());
        std::vector<int> parent(V, -1);
        std::vector<int> parentEdge(V, -1);
        dist[start] = 0.0;

        for (int i = 0; i < V - 1; ++i) {
            for (int ei = 0; ei < (int)edges.size(); ++ei) {
                const auto& e = edges[ei];
                
                if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                    dist[e.source] + e.weight < dist[e.destination]) {
                    dist[e.destination] = dist[e.source] + e.weight;
                    parent[e.destination] = e.source;
                    parentEdge[e.destination] = ei;
                }
            }
        }

        for (int ei = 0; ei < (int)edges.size(); ++ei) {
            const auto& e = edges[ei];
            
            if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                dist[e.source] + e.weight < dist[e.destination] - RELAX_EPS) {
                
                int v = e.destination;
                for (int i = 0; i < V; ++i) {
                    v = parent[v];
                }

                std::vector<int> cycle;
                int cur = v;
                do {
                    cycle.push_back(cur);
                    cur = parent[cur];
                } while (cur != v && cur != -1);
                
                if (cycle.empty()) continue;
                std::reverse(cycle.begin(), cycle.end());

                const int n = (int)cycle.size();
                std::vector<int> cycleEdgeIdx;
                cycleEdgeIdx.reserve(n);
                bool edgesOk = true;
                
                for (int i = 0; i < n; ++i) {
                    int toNode = cycle[(i + 1) % n];
                    int pe = parentEdge[toNode];
                    
                    if (pe < 0 || 
                        edges[pe].source != cycle[i] || 
                        edges[pe].destination != toNode) {
                        edgesOk = false;
                        break;
                    }
                    cycleEdgeIdx.push_back(pe);
                }
                
                if (!edgesOk) continue;

                double profit = 1.0;
                for (int pe : cycleEdgeIdx) {
                    double p = edges[pe].price;
                    if (!std::isfinite(p) || p <= 0.0) {
                        profit = std::numeric_limits<double>::quiet_NaN();
                        break;
                    }
                    profit *= p;
                    if (!std::isfinite(profit)) break;
                }

                if (!std::isfinite(profit)) continue;
                if (profit <= 0.0 || profit > PROFIT_MAX_LOCAL) continue;
                if ((int)cycle.size() < MIN_CYCLE_LEN) continue;
                if (profit < PROFIT_MIN_LOCAL) continue;

                std::string sig = canonicalSignature(cycle, profit);
                if (isDuplicateCycle(sig)) continue;

                std::ostringstream path;
                for (int nidx : cycle) {
                    path << nodeNames[nidx] << " -> ";
                }
                path << nodeNames[cycle.front()];

                std::time_t ts = clock_wall::to_time_t(clock_wall::now());
                std::tm ts_tm = *std::localtime(&ts);
                
                std::ostringstream pss;
                pss << std::fixed << std::setprecision(10) << profit;

                std::cout << "[" << std::put_time(&ts_tm, "%Y-%m-%d %H:%M:%S") << "] "
                          << "[!] Arbitraggio trovato! Profit = " << pss.str()
                          << "x | Percorso: " << path.str() << "\n";

                foundThisSecond++;
            }
        }
    }
}

void Graph::printGraphSummary(int maxEdgesToShow) {
    std::cout << "\n=== STATO ATTUALE DEL GRAFO ===\n";
    std::cout << "Nodi totali: " << nodeNames.size()
              << "\nArchi totali: " << edges.size() << std::endl;

    int countBinance = 0, countOKX = 0, countCross = 0;
    for (const auto& e : edges) {
        std::string src = nodeNames[e.source];
        std::string dst = nodeNames[e.destination];
        if (src.find("Cross") != std::string::npos || dst.find("Cross") != std::string::npos)
            countCross++;
        else if (src.find("OKX") != std::string::npos || dst.find("OKX") != std::string::npos)
            countOKX++;
        else if (src.find("Binance") != std::string::npos || dst.find("Binance") != std::string::npos)
            countBinance++;
    }

    std::cout << "  Archi Binance: " << countBinance
              << "\n  Archi OKX:     " << countOKX
              << "\n  Archi Cross:   " << countCross << std::endl;

    std::cout << "\n--- Elenco (max " << maxEdgesToShow << ") ---\n";
    int shown = 0;
    for (const auto& e : edges) {
        std::cout << nodeNames[e.source] << " -> " << nodeNames[e.destination]
                  << " | weight=" << e.weight
                  << " | price=" << std::exp(-e.weight) << std::endl;
        if (++shown >= maxEdgesToShow) break;
    }
    std::cout << "===============================\n";
}

void Graph::ensureSuperSourceEdges() {
    if (superSourceId == -1) superSourceId = addNode("SUPER_SOURCE");
    for (size_t i = lastSuperEdgeAddForNodeCount; i < nodeNames.size(); ++i)
        if ((int)i != superSourceId)
            addOrUpdateEdge("SUPER_SOURCE", nodeNames[i], 1.0, "Cross", "SUPER");
    lastSuperEdgeAddForNodeCount = nodeNames.size();
}

bool Graph::warmupActive() {
    static bool init = false;
    static std::time_t start = 0;
    const int WARMUP_SECONDS = 3;
    std::time_t now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    if (!init) { init = true; start = now; }
    return (now - start < WARMUP_SECONDS) || nodeNames.size() < 3;
}

void Graph::findArbitrageSuperSource() {
    const int V = static_cast<int>(nodeNames.size());
    if (V == 0 || warmupActive()) return;
    
    ensureSuperSourceEdges();
    if (superSourceId < 0 || superSourceId >= V) return;

    using clock_wall = std::chrono::system_clock;

    static std::time_t lastSecond = 0;
    static int foundThisSecond = 0;

    std::time_t secNow = clock_wall::to_time_t(clock_wall::now());
    if (lastSecond == 0) lastSecond = secNow;
    
    if (secNow != lastSecond) {
        if (foundThisSecond == 0) {
            std::tm t = *std::localtime(&lastSecond);
            std::cout << "[SuperSource] --- Nessun arbitraggio tra "
                      << std::put_time(&t, "%H:%M:%S") << " e "
                      << std::put_time(std::localtime(&secNow), "%H:%M:%S")
                      << " ---\n";
        } else {
            std::tm t = *std::localtime(&lastSecond);
            std::cout << "[SuperSource] === Arbitraggi trovati @ " << std::put_time(&t, "%H:%M:%S")
                      << " => " << foundThisSecond << " ===\n\n";
        }
        foundThisSecond = 0;
        lastSecond = secNow;
    }

    static constexpr double RELAX_EPS = 1e-6;
    static constexpr double PROFIT_MIN_LOCAL = 1.000001;
    static constexpr double PROFIT_MAX_LOCAL = 10.0;

    std::vector<double> dist(V, std::numeric_limits<double>::infinity());
    std::vector<int> parent(V, -1);
    std::vector<int> parentEdge(V, -1);
    dist[superSourceId] = 0.0;

    for (int i = 0; i < V - 1; ++i) {
        for (int ei = 0; ei < (int)edges.size(); ++ei) {
            const auto& e = edges[ei];
            
            if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                dist[e.source] + e.weight < dist[e.destination]) {
                dist[e.destination] = dist[e.source] + e.weight;
                parent[e.destination] = e.source;
                parentEdge[e.destination] = ei;
            }
        }
    }

    for (int ei = 0; ei < (int)edges.size(); ++ei) {
        const auto& e = edges[ei];
        
        if (dist[e.source] != std::numeric_limits<double>::infinity() &&
            dist[e.source] + e.weight < dist[e.destination] - RELAX_EPS) {
            
            int v = e.destination;
            for (int i = 0; i < V; ++i) {
                v = parent[v];
            }

            std::vector<int> cycle;
            int cur = v;
            do {
                cycle.push_back(cur);
                cur = parent[cur];
            } while (cur != v && cur != -1);
            
            if (cycle.empty()) continue;
            std::reverse(cycle.begin(), cycle.end());

            const int n = (int)cycle.size();
            std::vector<int> cycleEdgeIdx;
            cycleEdgeIdx.reserve(n);
            bool edgesOk = true;
            
            for (int i = 0; i < n; ++i) {
                int toNode = cycle[(i + 1) % n];
                int pe = parentEdge[toNode];
                
                if (pe < 0 || 
                    edges[pe].source != cycle[i] || 
                    edges[pe].destination != toNode) {
                    edgesOk = false;
                    break;
                }
                cycleEdgeIdx.push_back(pe);
            }
            
            if (!edgesOk) continue;

            double profit = 1.0;
            for (int pe : cycleEdgeIdx) {
                double p = edges[pe].price;
                if (!std::isfinite(p) || p <= 0.0) {
                    profit = std::numeric_limits<double>::quiet_NaN();
                    break;
                }
                profit *= p;
                if (!std::isfinite(profit)) break;
            }

            if (!std::isfinite(profit)) continue;
            if (profit <= 0.0 || profit > PROFIT_MAX_LOCAL) continue;
            if ((int)cycle.size() < MIN_CYCLE_LEN) continue;
            if (profit < PROFIT_MIN_LOCAL) continue;

            std::string sig = canonicalSignature(cycle, profit);
            if (isDuplicateCycle(sig)) continue;

            std::ostringstream path;
            for (int nidx : cycle) {
                path << nodeNames[nidx] << " -> ";
            }
            path << nodeNames[cycle.front()];

            std::time_t ts = clock_wall::to_time_t(clock_wall::now());
            std::tm ts_tm = *std::localtime(&ts);
            
            std::ostringstream pss;
            pss << std::fixed << std::setprecision(10) << profit;

            std::cout << "[SuperSource] [" << std::put_time(&ts_tm, "%Y-%m-%d %H:%M:%S") << "] "
                      << "[!] Arbitraggio trovato! Profit = " << pss.str()
                      << "x | Percorso: " << path.str() << "\n";

            foundThisSecond++;
        }
    }
}

void Graph::findArbitrageQuiet(BenchmarkStats& stats) {
    const int V = static_cast<int>(nodeNames.size());
    if (V == 0) return;

    static constexpr double RELAX_EPS = 1e-6;
    static constexpr double PROFIT_MIN_LOCAL = 1.000001;
    static constexpr double PROFIT_MAX_LOCAL = 10.0;

    for (int start = 0; start < V; ++start) {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        std::vector<double> dist(V, std::numeric_limits<double>::infinity());
        std::vector<int> parent(V, -1);
        std::vector<int> parentEdge(V, -1);
        dist[start] = 0.0;

        stats.bellmanFordRuns++;

        for (int i = 0; i < V - 1; ++i) {
            for (int ei = 0; ei < (int)edges.size(); ++ei) {
                const auto& e = edges[ei];
                stats.edgesProcessed++;
                
                if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                    dist[e.source] + e.weight < dist[e.destination]) {
                    dist[e.destination] = dist[e.source] + e.weight;
                    parent[e.destination] = e.source;
                    parentEdge[e.destination] = ei;
                }
            }
        }

        for (int ei = 0; ei < (int)edges.size(); ++ei) {
            const auto& e = edges[ei];
            
            if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                dist[e.source] + e.weight < dist[e.destination] - RELAX_EPS) {
                
                int v = e.destination;
                for (int i = 0; i < V; ++i) {
                    v = parent[v];
                }

                std::vector<int> cycle;
                int cur = v;
                do {
                    cycle.push_back(cur);
                    cur = parent[cur];
                } while (cur != v && cur != -1);
                
                if (cycle.empty()) continue;
                std::reverse(cycle.begin(), cycle.end());

                const int n = (int)cycle.size();
                std::vector<int> cycleEdgeIdx;
                cycleEdgeIdx.reserve(n);
                bool edgesOk = true;
                
                for (int i = 0; i < n; ++i) {
                    int toNode = cycle[(i + 1) % n];
                    int pe = parentEdge[toNode];
                    
                    if (pe < 0 || 
                        edges[pe].source != cycle[i] || 
                        edges[pe].destination != toNode) {
                        edgesOk = false;
                        break;
                    }
                    cycleEdgeIdx.push_back(pe);
                }
                
                if (!edgesOk) continue;

                double profit = 1.0;
                for (int pe : cycleEdgeIdx) {
                    double p = edges[pe].price;
                    if (!std::isfinite(p) || p <= 0.0) {
                        profit = std::numeric_limits<double>::quiet_NaN();
                        break;
                    }
                    profit *= p;
                    if (!std::isfinite(profit)) break;
                }

                if (!std::isfinite(profit)) continue;
                if (profit <= 0.0 || profit > PROFIT_MAX_LOCAL) continue;
                if ((int)cycle.size() < MIN_CYCLE_LEN) continue;
                if (profit < PROFIT_MIN_LOCAL) continue;

                std::string sig = canonicalSignature(cycle, profit);
                if (isDuplicateCycle(sig)) continue;

                stats.cyclesFound++;
            }
        }

        auto endTime = std::chrono::high_resolution_clock::now();
        stats.totalTime += std::chrono::duration<double>(endTime - startTime).count();
    }
}

void Graph::findArbitrageSuperSourceQuiet(BenchmarkStats& stats) {
    const int V = static_cast<int>(nodeNames.size());
    if (V == 0) return;
    
    ensureSuperSourceEdges();
    if (superSourceId < 0 || superSourceId >= V) return;

    static constexpr double RELAX_EPS = 1e-6;
    static constexpr double PROFIT_MIN_LOCAL = 1.000001;
    static constexpr double PROFIT_MAX_LOCAL = 10.0;

    auto bellmanFord = [&](int startNode) {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        std::vector<double> dist(V, std::numeric_limits<double>::infinity());
        std::vector<int> parent(V, -1);
        std::vector<int> parentEdge(V, -1);
        dist[startNode] = 0.0;

        stats.bellmanFordRuns++;

        for (int i = 0; i < V - 1; ++i) {
            for (int ei = 0; ei < (int)edges.size(); ++ei) {
                const auto& e = edges[ei];
                stats.edgesProcessed++;
                
                if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                    dist[e.source] + e.weight < dist[e.destination]) {
                    dist[e.destination] = dist[e.source] + e.weight;
                    parent[e.destination] = e.source;
                    parentEdge[e.destination] = ei;
                }
            }
        }

        for (int ei = 0; ei < (int)edges.size(); ++ei) {
            const auto& e = edges[ei];
            
            if (dist[e.source] != std::numeric_limits<double>::infinity() &&
                dist[e.source] + e.weight < dist[e.destination] - RELAX_EPS) {
                
                int v = e.destination;
                for (int i = 0; i < V; ++i) {
                    v = parent[v];
                }

                std::vector<int> cycle;
                int cur = v;
                do {
                    cycle.push_back(cur);
                    cur = parent[cur];
                } while (cur != v && cur != -1);
                
                if (cycle.empty()) continue;
                std::reverse(cycle.begin(), cycle.end());

                const int n = (int)cycle.size();
                std::vector<int> cycleEdgeIdx;
                cycleEdgeIdx.reserve(n);
                bool edgesOk = true;
                
                for (int i = 0; i < n; ++i) {
                    int toNode = cycle[(i + 1) % n];
                    int pe = parentEdge[toNode];
                    
                    if (pe < 0 || 
                        edges[pe].source != cycle[i] || 
                        edges[pe].destination != toNode) {
                        edgesOk = false;
                        break;
                    }
                    cycleEdgeIdx.push_back(pe);
                }
                
                if (!edgesOk) continue;

                double profit = 1.0;
                for (int pe : cycleEdgeIdx) {
                    double p = edges[pe].price;
                    if (!std::isfinite(p) || p <= 0.0) {
                        profit = std::numeric_limits<double>::quiet_NaN();
                        break;
                    }
                    profit *= p;
                    if (!std::isfinite(profit)) break;
                }

                if (!std::isfinite(profit)) continue;
                if (profit <= 0.0 || profit > PROFIT_MAX_LOCAL) continue;
                if ((int)cycle.size() < MIN_CYCLE_LEN) continue;
                if (profit < PROFIT_MIN_LOCAL) continue;

                std::string sig = canonicalSignature(cycle, profit);
                if (isDuplicateCycle(sig)) continue;

                stats.cyclesFound++;
            }
        }

        auto endTime = std::chrono::high_resolution_clock::now();
        stats.totalTime += std::chrono::duration<double>(endTime - startTime).count();
    };

    bellmanFord(superSourceId);

    std::set<std::string> processedExchanges;
    
    for (int node = 0; node < V; ++node) {
        if (node == superSourceId) continue;
        
        std::string nodeName = nodeNames[node];
        std::string exchange = "";
        
        if (nodeName.find("_Binance") != std::string::npos) exchange = "Binance";
        else if (nodeName.find("_OKX") != std::string::npos) exchange = "OKX";
        else if (nodeName.find("_Bybit") != std::string::npos) exchange = "Bybit";
        
        if (exchange.empty() || processedExchanges.count(exchange)) continue;
        
        processedExchanges.insert(exchange);
        bellmanFord(node);
    }
}

void Graph::runBenchmark() {
    using clock_steady = std::chrono::steady_clock;
    
    static const int BENCHMARK_WARMUP_SECONDS = 10;
    static bool warmupDone = false;
    static auto warmupStart = clock_steady::now();
    static int lastWarmupSec = -1;
    
    if (!warmupDone) {
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            clock_steady::now() - warmupStart).count();
        
        if (elapsed != lastWarmupSec) {
            int remaining = BENCHMARK_WARMUP_SECONDS - (int)elapsed;
            if (remaining > 0) {
                std::cout << "[Benchmark Warmup] Collecting data... " 
                          << remaining << "s remaining\n";
                lastWarmupSec = (int)elapsed;
            }
        }
        
        if (elapsed >= BENCHMARK_WARMUP_SECONDS) {
            warmupDone = true;
            std::cout << "[Benchmark] Warmup complete. Starting benchmark...\n\n";
        }
        return;
    }
    
    if (nodeNames.empty()) return;

    static auto lastPrint = clock_steady::now();
    static int iterations = 0;
    
    static std::deque<std::string> cacheClassic;
    static std::unordered_set<std::string> setClassic;
    static const size_t MAX_CACHE = 100;
    
    static std::deque<std::string> cacheSuper;
    static std::unordered_set<std::string> setSuper;
    
    auto backupCache = recentCycles;
    auto backupSet = recentSet;
    
    recentCycles = cacheClassic;
    recentSet = setClassic;
    
    findArbitrageQuiet(statsClassic);
    
    cacheClassic = recentCycles;
    setClassic = recentSet;
    
    recentCycles = backupCache;
    recentSet = backupSet;
    
    backupCache = recentCycles;
    backupSet = recentSet;
    
    recentCycles = cacheSuper;
    recentSet = setSuper;
    
    findArbitrageSuperSourceQuiet(statsSuper);
    
    cacheSuper = recentCycles;
    setSuper = recentSet;
    
    recentCycles = backupCache;
    recentSet = backupSet;
    
    iterations++;

    auto now = clock_steady::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
        now - lastPrint).count();
    
if (elapsed >= 5) {
    auto now_time = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    std::cout << "\n========== BENCHMARK REPORT (" 
            << std::put_time(std::localtime(&now_time), "%Y-%m-%d %H:%M:%S") 
            << ") ==========\n";    std::cout << "Iterations: " << iterations << "\n";
    std::cout << "Graph size: " << nodeNames.size() << " nodes, " 
              << edges.size() << " edges\n";
    
    if (setClassic.size() != setSuper.size()) {
        std::cout << "Note: Cycle count difference due to microlatency between runs\n";
        std::cout << "      (price changes between Classic and Super-Source execution)\n";
    }
    std::cout << "\n";
    
    std::cout << "[Classic Mode - Multi-Source Bellman-Ford]\n";
    std::cout << "  Cycles found:       " << statsClassic.cyclesFound << "\n";
    std::cout << "  Bellman-Ford runs:  " << statsClassic.bellmanFordRuns << "\n";
    std::cout << "  Edges processed:    " << statsClassic.edgesProcessed << "\n";
    std::cout << "  Total time:         " << std::fixed << std::setprecision(3) 
              << statsClassic.totalTime << "s\n";
    std::cout << "  Avg time/iteration: " << std::fixed << std::setprecision(3)
              << (statsClassic.totalTime / iterations) << "s\n\n";
    
    std::cout << "[Super-Source Hybrid Mode - 4x Bellman-Ford] - (1x super-source + 1x per exchange)\n";
    std::cout << "  Cycles found:       " << statsSuper.cyclesFound << "\n";
    std::cout << "  Bellman-Ford runs:  " << statsSuper.bellmanFordRuns << "\n";
    std::cout << "  Edges processed:    " << statsSuper.edgesProcessed << "\n";
    std::cout << "  Total time:         " << std::fixed << std::setprecision(3) 
              << statsSuper.totalTime << "s\n";
    std::cout << "  Avg time/iteration: " << std::fixed << std::setprecision(3)
              << (statsSuper.totalTime / iterations) << "s\n\n";
    
    if (statsSuper.totalTime > 0) {
        double speedup = statsClassic.totalTime / statsSuper.totalTime;
        std::cout << "Performance:\n";
        std::cout << "  Speedup: " << std::fixed << std::setprecision(2) 
                  << speedup << "x faster\n";
        std::cout << "  Time savings: " << std::fixed << std::setprecision(1) 
                  << ((speedup - 1.0) * 100) << "%\n";
        std::cout << "  BF reduction: " << std::fixed << std::setprecision(1)
                  << ((double)statsClassic.bellmanFordRuns / statsSuper.bellmanFordRuns) 
                  << "x fewer runs\n";
    }
    
    std::cout << "=======================================================\n\n";
    
    lastPrint = now;
    iterations = 0;
    statsClassic = BenchmarkStats();
    statsSuper = BenchmarkStats();
    
    cacheClassic.clear();
    setClassic.clear();
    cacheSuper.clear();
    setSuper.clear();
    }
}