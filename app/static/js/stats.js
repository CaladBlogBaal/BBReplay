document.addEventListener('DOMContentLoaded', async function() {
    try {
        await setTotalReplays();
        await setTotalPlayers();
        await setPeakHours();
        await getCharacterData();
        await getReplayTimestamps();
        await initializeIcons();
        await matchupRarity();
        await loadMatchups(); // No need to await if it doesn’t return a promise
    } catch (error) {
        console.error("An error occurred during initialization:", error);
    }
});

let ICONS = [];

async function fetchData(url, error_message) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error('Error: Response not OK', response.statusText);
            return;
        }
        return await response.json();
    } catch (error) {
        console.error(error_message, error);
    }
}

async function setTotalReplays() {
    const totalReplays = await fetchData('/api/replay/total', 'Error fetching total players: ');
    const totalReplayElement = document.querySelector('#totalReplays h3');
    totalReplayElement.textContent = `Total Replays: ${totalReplays}`;
}

async function setPeakHours() {
    const totalReplayElement = document.querySelector('#peakHours h5');
    totalReplayElement.textContent = `Peak Hours`;
}

async function matchupRarity() {
    const matchupRarity = await fetchData('/api/replay/matchup-rarity', 'Error fetching matchup rarity: ')
    const mostCommon = matchupRarity[matchupRarity.length - 1];
    const leastCommon = matchupRarity[0];

    const matchupRarityElement = document.getElementById('matchupRarity');

    function createRarityCard(matchup) {

        const box = document.createElement('li');
        box.classList.add('mt-4', 'mb-4');
        const boxTitle = document.createElement('h5');
        boxTitle.textContent = `${matchup.character_1_name } vs ${matchup.character_2_name}`

        const imgWrapper = document.createElement('div');
        imgWrapper.className = 'responsive-container';

        const imgDiv = document.createElement('p');
        imgDiv.className = 'imgFloatLeft';
        const img = document.createElement('img');

        img.src = fetchCharacterIcons(matchup.character_1_id);
        img.className = 'bordered';
        imgDiv.appendChild(img);

        const imgDiv2 = document.createElement('p');
        imgDiv2.className = 'imgFloatRight';
        const img2 = document.createElement('img');
        img2.src = fetchCharacterIcons(matchup.character_2_id);
        img2.className = 'bordered';
        imgDiv2.appendChild(img2);

        // Append both image divs to the wrapper
        imgWrapper.appendChild(imgDiv);
        imgWrapper.appendChild(imgDiv2);
        const container = document.createElement('ul');
        const titleDiv = document.createElement('li');
        titleDiv.textContent = `Percentage of replays: `;
        const valueDiv = document.createElement('p');
        const span = document.createElement('span')
        span.textContent = `${matchup.percentage}`
        valueDiv.textContent = '%';
        valueDiv.appendChild(span);

        titleDiv.appendChild(valueDiv);
        container.appendChild(titleDiv);

        box.appendChild(imgWrapper); // Append imgWrapper instead of individual imgDivs
        box.appendChild(boxTitle);
        box.appendChild(container);

        matchupRarityElement.appendChild(box); // Append column to the row
        }

        createRarityCard(mostCommon);
        createRarityCard(leastCommon);

        const cards = document.getElementsByClassName('mt-4 mb-4');
        const commonCard = cards[0];
        const leastCommonCard = cards[cards.length - 1];

        commonCardTitle = document.createElement('H3');
        commonCardTitle.textContent = 'Most Common Matchup';
        leastComonCardTitle = document.createElement('H3');
        leastComonCardTitle.textContent = 'Least Common Matchup';
        commonCard.insertBefore(commonCardTitle, commonCard.firstChild);
        leastCommonCard.insertBefore(leastComonCardTitle, leastCommonCard.firstChild);

}

async function getReplayTimestamps() {
    const timestamps = await fetchData('api/replay-timestamps', 'Error fetching timestamps: ');
    const hourCounts = Array(24).fill(0);

    timestamps.forEach(timestamp => {
        const date = new Date(timestamp);
        const hour = date.getUTCHours();
        hourCounts[hour]++;
    });

    const labels = Array.from({length: 24}, (_, i) => `${i}:00`);  // ["0:00", "1:00", ..., "23:00"]

    const data = {
        labels: labels,
        datasets: [{
            label: 'Players',
            data: hourCounts,
            backgroundColor: 'rgba(70, 70, 70, 0.9)',
            borderColor: 'rgba(70, 70, 70, 1)',
            borderWidth: 1
        }]
    };

    const config = {
        type: 'bar',
        data: data,
        options: {
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Hour of the Day (UTC)'
                    },
                    grid: {
                      color: "black"
                    },
                     ticks: {
                      color: "black"
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Players'
                    },
                    beginAtZero: true,
                    grid: {
                      color: "black"
                    },
                     ticks: {
                      color: "black"
                    }
                }
            }
        }
    };

    const ctx = document.getElementById('peakHoursChart').getContext('2d');
    new Chart(ctx, config);
}

async function getCharacterData() {
    const totalCh = await fetchData('api/replay/total-per-character', 'Error fetching total per character: ');

    const sortedData = totalCh.sort((a, b) => b.total - a.total);

    // Function to get labels and values based on the number of entries to display
    function getDataToDisplay(limit) {
        const displayedData = sortedData.slice(0, limit);
        return {
            labels: displayedData.map(item => `${item.character_name}`),
            values: displayedData.map(item => item.total)
        };
    }

    let chartData = getDataToDisplay(5);
    // Create the chart
    let characterChart = new Chart(
        document.getElementById('characterChart'),
        {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Replays',
          data: chartData.values,
          backgroundColor: 'rgba(70, 70, 70, 0.9)',
          borderColor: 'rgba(70, 70, 70, 1)',
          borderWidth: 1
        }]
      },
      options: {
        indexAxis: 'y', // This makes the chart horizontal
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: "black"
            },
            ticks: {
              color: "#400040"
            }
          },
          y: {
            grid: {
              color: "black"
            },
             ticks: {
              color: "black"
            }
          }
        },
        plugins: {
          legend: {
            display: false
          }
        }
      }
    });
    // Toggle button functionality
    const button = document.getElementById('toggleButton');
    let showAll = false;
    button.addEventListener('click', () => {
        showAll = !showAll;
        const limit = showAll ? sortedData.length : 5;
        chartData = getDataToDisplay(limit);

        // Update chart data and re-render
        characterChart.data.labels = chartData.labels;
        characterChart.data.datasets[0].data = chartData.values;
        characterChart.update();

        // Update button text
        button.textContent = showAll ? 'Show Top 5' : 'Show All Characters';
    });
}

async function setTotalPlayers() {
    const totalPlayers = await fetchData('/api/replay/total-players', 'Error fetching total unique players:');
    const totalPlayersElement = document.querySelector('#totalPlayers h3');
    totalPlayersElement.textContent = `Unique Players: ${totalPlayers.total}`;
}

async function initializeIcons() {
    ICONS = await fetchData('/api/character-icons', 'Error fetching character icon:');
}

async function loadMatchups() {
    const data = await fetchData('api/replay/character-matchup-stats', 'Error fetching replays')
    populateMatchupList(data);

}

function fetchCharacterIcons(iconID) {
    const icon = ICONS.find(js => js.id === Number(iconID));
    return icon ? icon.path : null;
}
function populateMatchupList(data) {
    const characterGrid = document.getElementById('character-grid');
    const matchupTitle = document.getElementById('matchupTitle');

    // Group matchups by character
    const characterMatchups = data.reduce((acc, matchup) => {
        const {
            character_1_id,
            character_1_name,
            character_2_name,
            character_2_id,
            matches_played,
            character_1_win_rate,
            character_2_win_rate
        } = matchup;

        if (!acc[character_1_id]) acc[character_1_id] = { name: character_1_name, id: character_1_id, matchups: [] };
        if (!acc[character_2_id]) acc[character_2_id] = { name: character_2_name, id: character_2_id, matchups: [] };

        acc[character_1_id].matchups.push({
            opponent: character_2_name,
            count: matches_played,
            percentage: character_1_win_rate
        });
        acc[character_2_id].matchups.push({
            opponent: character_1_name,
            count: matches_played,
            percentage: character_2_win_rate
        });

        return acc;
    }, {});


    Object.values(characterMatchups).forEach(character => {
        const characterCard = document.createElement('li');
        const textWrapper = document.createElement('p');
        characterCard.classList.add('ml-4', 'mr-4', 'character-card');
        textWrapper.textContent = character.name;
        const charIcon = document.createElement('img');
        charIcon.className = 'bordered';
        charIcon.src = fetchCharacterIcons(character.id);
        charIcon.width = 72;
        charIcon.height = 72;
        charIcon.classList.add('bordered', 'selectable');
        characterCard.addEventListener('click', () => {
            document.querySelectorAll('.selected').forEach(selected => {
                selected.classList.remove('selected');
            });

            charIcon.classList.add('selected');
            displayMatchups(character);
        });
        characterCard.appendChild(charIcon);
        characterCard.appendChild(textWrapper);
        characterGrid.appendChild(characterCard);
    });

    const table = $('#matchupTable').DataTable({
        scrollY: '40vh', // Sets table height to 40% of viewport
        scrollCollapse: true,
        responsive: true,
        columnDefs: [
        { responsivePriority: 1, targets: 0 },
        { responsivePriority: 2, targets: -1 }
        ],
        layout: {
        topStart: {
            buttons: ['copyHtml5', 'excelHtml5', 'csvHtml5', 'pdfHtml5']
        }
    }
    });

    function displayMatchups(character) {
        // Clear existing matchups
        table.clear().draw();
        matchupTitle.innerHTML = '';
        const matchups = characterMatchups[character.id];
        if (!matchups) return;

        // Title for the selected character
        const title = document.createElement('h5');
        title.textContent = `${character.name}'s Matchups`;
        matchupTitle.appendChild(title);

        // Populate the matchup table
        character.matchups.forEach(({ opponent, count, percentage }) => {
            table.row.add([
                opponent,
                percentage,
                count
            ]).draw(false); // Add row and do not redraw the table yet

        });

    }
}