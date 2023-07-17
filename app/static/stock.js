function setInterval(value) {
    let input = document.getElementById("interval");
    input.value = value;
    let form = document.getElementById("pickInterval");
    form.submit();
}

const changeBuySignals = () => {
    const rows = document.querySelectorAll("#stockScreenerRating tbody tr:not(.hidden)");

    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
        let row = rows[rowIndex];
        let cells = row.querySelectorAll("td");
        for (let cell of cells) {
            let {textContent: current} = cell;
            cell.style.padding = "0.15rem";
            let colIndex = cell.cellIndex;
            if (cells.length === 6) {
                if (colIndex === 0) {
                    cell.style.textAlign = "center";
                } else if (colIndex === 1) {
                    const re = /(\d+\.\d+)\s+(-?\d+\.\d+)/;
                    const result = re.exec(current);
                    const latest_price = result[1];
                    const latest_change = result[2];

                    if (latest_change.includes("-")) {
                        cell.innerHTML = `<span style="font-size: 1rem; color: #ff2f92">` + latest_price + `&nbsp;</span><span style="font-size: 0.75rem; background-color: #ff2f92; color: #ffffff; padding: 0.1rem; border-radius: 0.15rem;">` + latest_change.replace(/^-/, "") + `</span>`;
                    } else {
                        cell.innerHTML = `<span style="font-size: 1rem; color: #0055cc">` + latest_price + `&nbsp;</span><span style="font-size: 0.75rem; background-color: #0055cc; color: #ffffff; padding: 0.1rem; border-radius: 0.15rem;">` + latest_change + `</span>`;
                    }
                } else if (colIndex === 2) {
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
                        case "STRONG_SELL":
                            cell.innerHTML = `<span class="signal strong-sell">Strong sell</span>`;
                            break;
                        default:
                            break;
                    }
                } else if (colIndex === 3 || colIndex === 4 || colIndex === 5) {
                    cell.style.border = "1px solid #ffffff";
                    let value = parseInt(current);
                    let percentage = Math.round(value / 26 * 100);

                    switch (colIndex) {
                        case 3:
                            cell.innerHTML = `<span style="color: #0055cc">` + value + `</span>`;
                            cell.style.background = `linear-gradient(90deg, rgba(0, 85, 204, 0.85) ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                            break;
                        case 4:
                            cell.innerHTML = `<span style="color: #a844c2">` + value + `</span>`;
                            cell.style.background = `linear-gradient(90deg, rgba(168, 68, 194, 0.85) ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                            break;
                        case 5:
                            cell.innerHTML = `<span style="color: #ff2f92">` + value + `</span>`;
                            cell.style.background = `linear-gradient(90deg, rgba(255, 47, 146, 0.85) ${percentage}%, rgba(255, 255, 255, 0) ${percentage}%)`;
                            break;
                        default:
                            break;
                    }
                }
            } else {
                if (colIndex === 0) {

                } else if (colIndex === 1) {
                    cell.innerHTML = Number(current).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                }
            }
        }
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", changeBuySignals);
} else {
    changeBuySignals();
}

function toggleDetails(event) {

    let row = event.target.closest("tr");
    let detailsRow = row.nextElementSibling;
    detailsRow.classList.toggle("hidden");
}