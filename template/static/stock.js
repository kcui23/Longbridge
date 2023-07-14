function setInterval(value) {
    let input = document.getElementById("interval");
    input.value = value;
    let form = document.getElementById("pickInterval");
    form.submit();
}

const changeBuySignals = () => {
    const cells = document.querySelectorAll("#stockScreener td");
    for (let cell of cells) {
        let {textContent: current} = cell;
        cell.style.padding = "0.15rem";

        let colIndex = cell.cellIndex;
        if (colIndex === 2) {
            cell.style.textAlign = "center";
            switch (current) {
                case "STRONG_BUY":
                    cell.innerHTML = `<span class="signal strong-buy">Strong buy</span>`;
                    break;
                case "BUY":
                    cell.innerHTML = `<span class="signal buy">Buy</span>`;
                    break;
                case "NEUTRAL":
                    cell.innerHTML = `<span class="signal neutral">Neutral</span>`;
                    break;
                case "SELL":
                    cell.innerHTML = `<span class="signal sell">Sell</span>`;
                    break;
                case "STRONG SELL":
                    cell.innerHTML = `<span class="signal strong-sell">Strong sell</span>`;
                    break;
                default:
                    break;
            }
        }

        if (colIndex === 3 || colIndex === 4 || colIndex === 5) {
            cell.style.border = "1px solid #ffffff";
            let value = parseInt(current);
            let percentage = Math.round(value / 26 * 100);

            switch (colIndex) {
                case 3:
                    cell.style.background = `linear-gradient(90deg, #0055cc ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                    break;
                case 4:
                    cell.style.background = `linear-gradient(90deg, #a844c2 ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                    break;
                case 5:
                    cell.style.background = `linear-gradient(90deg, #ff2f92 ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                    break;
                default:
                    break;
            }
        }
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", changeBuySignals);
} else {
    changeBuySignals();
}