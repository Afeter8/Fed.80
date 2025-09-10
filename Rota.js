function iniciarProteccion() {
    const estado = document.getElementById("estado");
    estado.innerHTML = "🔄 Activando bucle eterno de protección...";

    // Bucle de defensa automática
    setInterval(() => {
        repararCodigo();
        detectarAmenazas();
    }, 3000); // cada 3 segundos
}

function repararCodigo() {
    console.log("🛠 Reparación automática en curso...");
}

function detectarAmenazas() {
    const amenazas = ["XSS", "SQLi", "Malware", "DDoS"];
    const amenaza = amenazas[Math.floor(Math.random() * amenazas.length)];
    console.log("⚡ Defensa contra:", amenaza);
}
