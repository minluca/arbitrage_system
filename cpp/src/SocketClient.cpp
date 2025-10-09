#include "SocketClient.hpp"
#include <iostream>
#include <string>
#include <winsock2.h>

#pragma comment(lib, "ws2_32.lib")

namespace Socket 
{
    Client::Client(const std::string ip, int port) 
    {
        // inizializza Winsock
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
            std::cerr << "[Client] Errore WSAStartup" << std::endl;
            exit(1);
        }

        _socket = socket(AF_INET, SOCK_STREAM, 0);
        if (_socket == INVALID_SOCKET) {
            std::cerr << "[Client] Errore creazione socket" << std::endl;
            WSACleanup();
            exit(1);
        }

        sockaddr_in serv_addr{};
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        serv_addr.sin_addr.s_addr = inet_addr(ip.c_str());

        if (connect(_socket, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
            std::cerr << "[Client] Errore connessione" << std::endl;
            closesocket(_socket);
            WSACleanup();
            exit(1);
        }

        std::cout << "[Client] Connesso a " << ip << ":" << port << std::endl;
    }

    Client::~Client() 
    {
        closesocket(_socket);
        WSACleanup();
    }

    void Client::sendMessage(const std::string& message) 
    {
        std::string length_str = std::to_string(message.length());
        std::string message_length = std::string(message_size_length - length_str.length(), '0') + length_str;

        send(_socket, message_length.c_str(), message_size_length, 0);
        send(_socket, message.c_str(), (int)message.length(), 0);
    }

    std::string Client::receiveMessage() 
    {
        char message_length[message_size_length + 1] = {0};
        recv(_socket, message_length, message_size_length, 0);
        int length = std::stoi(message_length);

        std::string message;
        message.resize(length);
        recv(_socket, &message[0], length, 0);

        return message;
    }
}