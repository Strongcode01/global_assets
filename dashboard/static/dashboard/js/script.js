document.addEventListener("DOMContentLoaded", () => {
  const linkBtn = document.querySelector(".btn");
  if (window.ethereum) {
    linkBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        alert(`Wallet connected: ${accounts[0]}`);
      } catch (err) {
        alert("Wallet connection failed!");
      }
    });
  }
});
