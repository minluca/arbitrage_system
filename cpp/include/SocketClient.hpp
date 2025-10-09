#pragma once
#include <string>

namespace Socket 
{
    const int message_size_length = 16;

    class Client 
    {
    private:
        int _socket;            

    public:
        Client(const std::string ip, int port);
        ~Client();

        void sendMessage(const std::string& message);
        std::string receiveMessage();
    };
}