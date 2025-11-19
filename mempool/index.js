const { ethers } = require("ethers");

// Add your Quicknode Ethereum WSS endpoint here
const url = "wss://indulgent-winter-bush.quiknode.pro/e162b5fcebd0055602eed695732927ee2a0fa669/";

// Connect to the WebSocket provider
const provider = new ethers.WebSocketProvider(url);

// Listen for pending transactions
const init = () => {
    provider.on("pending", async (txHash) => {
        try {
            const tx = await provider.getTransaction(txHash);
            if (tx) {
                console.log(tx);
            }
        } catch (err) {
            console.error(`Error fetching transaction ${txHash}:`, err);
        }
    });

    console.log("Listening for pending transactions...");
};

init();