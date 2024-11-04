import replayLoader from "./infinite_scroll.js";
import replayManager from "./search.js";


function formatDates(dates) {
  return dates.map(dateString => {
    // Split the date string into day, month, and year
    const [day, month, year] = dateString.split('/');
    // Create a new Date object
    const dateObject = new Date(`${year}-${month}-${day}`);
    // Format the date to MMMM D, YYYY
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return dateObject.toLocaleDateString("en-US", options);
  });
}


function populateFieldsWithParameters() {
    if (window.location.href.includes('upload')) return;
    const searchParams = new URLSearchParams(window.location.search);
    const dateInput = $('#dateField');
    const playerInput = document.getElementById('playerInput');
    const playerInput2 = document.getElementById('playerInput2');

    function handleCharacterIcon(fieldValue, dropdownID, characterContainerID) {

        function changeIcon(collection) {
            Array.prototype.forEach.call(collection, function(item) {
            const aTag = item.getElementsByTagName('a')[0];
            const dataID = aTag.getAttribute('data-id');
            if (dataID === fieldValue) {
                if (fieldValue !== '') {
                    const imgPath = aTag.getElementsByTagName('img')[0].getAttribute('src');
                    characterDropdown.style.background = `url(${imgPath}) no-repeat center center`;
                    characterDropdown.style.backgroundSize = 'cover';
                } else {
                    characterDropdown.style.background = '';
                }
            }
        });

        }

        const characterDropdown = document.getElementById(dropdownID);
        const characterContainer = document.getElementById(characterContainerID);

        let collection = characterContainer.getElementsByClassName('dropdown-item');
        // Call the function directly in case the items are already there
        if (collection.length > 0) {
            changeIcon(collection);
        } else {
            // Create a MutationObserver instance
            const observer = new MutationObserver((mutationsList, observer) => {
                for (let mutation of mutationsList) {
                    if (mutation.type === 'childList') {
                        collection = characterContainer.getElementsByClassName('dropdown-item');
                        if (collection.length > 0) {
                            changeIcon(collection);
                            observer.disconnect();
                        }
                    }
                }
            });

            // Start observing the characterContainer for child node additions
            observer.observe(characterContainer, { childList: true, subtree: true });
        }


    }
    for (const [key, value] of searchParams.entries()) {
        if (key === 'recorded_at') {
          const dates = JSON.parse(value);
          // Format the dates
          const formattedDates = formatDates(dates);
          const [startDate, endDate] = formattedDates;
          dateInput.data('daterangepicker').setStartDate(startDate);
          dateInput.data('daterangepicker').setEndDate(endDate);

        } else if (key === 'p1') {
            playerInput.value = value;
        } else if (key === 'p2') {
            playerInput2.value = value;
        } // else if (key === 'p1_character_id') {
          //  handleCharacterIcon(value,'characterDropdown', 'characterContainer');
        //} else if (key === 'p2_character_id') {
        //    handleCharacterIcon(value, 'characterDropdown2', 'characterContainer2');
       // }
    }
    const value = searchParams.get('p1_character_id') || '';
    const value2 = searchParams.get('p2_character_id') || '';
    handleCharacterIcon(value,'characterDropdown', 'characterContainer');
    handleCharacterIcon(value2, 'characterDropdown2', 'characterContainer2');
}

// https://developer.mozilla.org/en-US/docs/Web/API/History_API/Working_with_the_History_API#using_pushstate
window.addEventListener("popstate", (event) => {
    if (event.state) {
        const replayContainer = document.getElementById('replaysContainer')
        replayContainer.replaceChildren();
        replayLoader.maxPage = event.state.maxPage;
        replayLoader.replayString = new URLSearchParams(window.location.search);
        // Convert page to a number before adding 1
        replayLoader.page = Number(replayLoader.replayString.get('page')) + 1 || 1;
        event.state.replays.forEach(replay => {
          $('#replaysContainer').append(replayLoader.renderReplay(replay));
        });
        replayLoader.replayString.set('page', replayLoader.page.toString());

      $(document).ready(function () {
          populateFieldsWithParameters();
      })
  }
});

$(document).ready(function() {
    replayManager.init().then(
        populateFieldsWithParameters()
    );
    replayLoader.loadReplays(new URLSearchParams(window.location.search)).then(
        r => history.replaceState(r, '', window.location.search)
    );
});
