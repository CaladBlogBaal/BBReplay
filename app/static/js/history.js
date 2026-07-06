import replayLoader from './infinite_scroll.js?v=1.0.2';
import replayManager from './search.js?v=1.0.2';

function formatDates(dates) {
    return dates.map(dateString => {
        const [day, month, year] = dateString.split('/');
        return new Date(`${year}-${month}-${day}`).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric',
        });
    });
}

function populateFieldsWithParameters() {
    if (window.location.href.includes('upload')) return;
    const searchParams = new URLSearchParams(window.location.search);
    const dateInput = $('#dateField');
    const playerInput = document.getElementById('playerInput');
    const playerInput2 = document.getElementById('playerInput2');

    function handleCharacterIcon(fieldValue, dropdownID, characterContainerID) {
        const characterDropdown = document.getElementById(dropdownID);
        const characterContainer = document.getElementById(characterContainerID);

        function changeIcon(collection) {
            Array.prototype.forEach.call(collection, item => {
                const aTag = item.getElementsByTagName('a')[0];
                if (aTag.getAttribute('data-id') !== fieldValue) return;
                if (fieldValue !== '') {
                    const imgPath = aTag.getElementsByTagName('img')[0].getAttribute('src');
                    characterDropdown.style.background = `url(${imgPath}) no-repeat center center`;
                    characterDropdown.style.backgroundSize = 'cover';
                } else {
                    characterDropdown.style.background = '';
                }
            });
        }

        let collection = characterContainer.getElementsByClassName('dropdown-item');
        if (collection.length > 0) {
            changeIcon(collection);
        } else {
            const observer = new MutationObserver(mutations => {
                if (!mutations.some(mutation => mutation.type === 'childList')) return;
                collection = characterContainer.getElementsByClassName('dropdown-item');
                if (collection.length > 0) {
                    changeIcon(collection);
                    observer.disconnect();
                }
            });
            observer.observe(characterContainer, { childList: true, subtree: true });
        }
    }

    // Clear values that may belong to the history entry we just left.
    playerInput.value = searchParams.get('p1') || '';
    playerInput2.value = searchParams.get('p2') || '';
    if (searchParams.has('datetime_')) {
        const [startDate, endDate] = formatDates(JSON.parse(searchParams.get('datetime_')));
        dateInput.data('daterangepicker').setStartDate(startDate);
        dateInput.data('daterangepicker').setEndDate(endDate);
    } else {
        dateInput.val('');
    }

    handleCharacterIcon(
        searchParams.get('p1_character_id') || searchParams.get('p1_toon') || '',
        'characterDropdown',
        'characterContainer',
    );
    handleCharacterIcon(
        searchParams.get('p2_character_id') || searchParams.get('p2_toon') || '',
        'characterDropdown2',
        'characterContainer2',
    );
}

async function restoreFromLocation({ replaceHistory = false } = {}) {
    const query = new URLSearchParams(window.location.search);
    query.set('page', '1');
    replayManager.replayString = replayLoader.cloneParams(query)
    populateFieldsWithParameters();

    const result = await replayLoader.startSearch(query);
    // history only replaces with searches that actually became the active displayed result
    if (replaceHistory && result?.accepted) {
        history.replaceState(result.historyState, '', `?${query.toString()}`);
    }
    return result;
}

window.addEventListener('popstate', () => {
    // Never restore cached DOM/pagination metadata independently of its query.
    // Re-run the URL's search as a new generation so in-flight work is invalidated.
    restoreFromLocation().catch(error => {
        console.error('Restore from history failed:', error);
    });
});

async function bootBBReplay() {
    console.log('Boot started');

    try {
        console.log('replayManager.init starting');
        replayManager.init();
        console.log('replayManager.init finished');
    } catch (error) {
        console.error('replayManager.init failed:', error);
    }

    try {
        console.log('populateFieldsWithParameters starting');
        populateFieldsWithParameters();
        console.log('populateFieldsWithParameters finished');
    } catch (error) {
        console.error('populateFieldsWithParameters failed:', error);
    }

    try {
        console.log('restoreFromLocation starting');
        const result = await restoreFromLocation({ replaceHistory: true });
        console.log('restoreFromLocation finished:', result);
    } catch (error) {
        console.error('restoreFromLocation failed:', error);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootBBReplay, { once: true });
} else {
    bootBBReplay();
}

export { populateFieldsWithParameters, restoreFromLocation };