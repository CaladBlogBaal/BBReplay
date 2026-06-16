// Encapsulating state within an object
const replayLoader = {
    page: new URLSearchParams(window.location.search).get('page') || 1,
    maxPage: Infinity,
    loading: false,
    replayString: new URLSearchParams(window.location.search),
    currentController: null,

    async loadReplays(params = new URLSearchParams(this.replayString), cancelPrevious = false) {

        if (cancelPrevious && this.currentController) {
            this.currentController.abort();
        }

        if (this.loading && !cancelPrevious) return;

        this.currentController = new AbortController();

        if (this.page > this.maxPage || params.get('page') > this.maxPage) {
            this.page = 1;
            return;
        }

        this.loading = true;

        if (params.toString() !== this.replayString.toString()) {
            this.page = 1;
            this.maxPage = Infinity;
            params.set('page', '1');
            this.replayString = new URLSearchParams(params);
        }

        $('#loading').show();

        try {

            const response = await fetch(`api/replay-sets?${params.toString()}`,{
            signal: this.currentController.signal
            });

            if (!response.ok) {
                if (response.status === 404) {
                    // block the pagination
                    this.maxPage = 0;
                    return;
                }
                console.error('Error: Response not OK', response.statusText);
                return;
            }

            const data = await response.json();

            if (this.currentController.signal.aborted) return;

            if (data.replays.length === 0) {
                this.maxPage = this.page - 1;
            } else {
                data.replays.forEach(replay => {
                    $('#replaysContainer').append(this.renderReplay(replay));
                });
            }

            this.maxPage = data.max_page;

            // do not block pagination if only one page is available
            if (this.maxPage === 1) {
                this.maxPage = Infinity;
            }
            // check if it's just not page for a parameter
            // if (Array.from(this.replayString.keys()).length !== 1)  {
            //    window.history.pushState(data, '', '?' + this.replayString.toString());
            // }
            this.page++;
            this.replayString.set('page', this.page.toString());
            return data;

        } catch (error) {
            console.error('Error fetching replays', error);
        } finally {
            this.loading = false;
            $('#loading').hide();
        }
    },

 renderReplay: function (replay) {
    // Get the computed styles of the root element
    const root = document.documentElement;
    const styles = getComputedStyle(root);
    const amber = 'rgba(50, 68, 168, 0.7)';
    const dusty = 'rgba(163, 27, 27, 0.7)';
    const granite = styles.getPropertyValue('--granite').trim();

    const createElementWithClass = (tag, className) => {
        const element = document.createElement(tag);
        if (className) {
            element.className = className;
        }
        return element;
    };

    const container = createElementWithClass('div', 'row no-gutters align-center justify-center');

    const createPlayerCard = (player, icon, wins) => {
        const col = createElementWithClass('div', 'col-12 col-sm-6 col-md-5 mb-3');
        const card = createElementWithClass('div', 'card card-custom card-body text-center');
        card.style.width = '18rem';

        const row = createElementWithClass('div', 'row align-items-center shadow-custom');
        const imgCol = createElementWithClass('div', 'col-12');
        const img = createElementWithClass('img', 'shadow bg-black rounded img-custom');
        img.src = `/static/img/${icon}`;
        img.alt = icon;
        imgCol.appendChild(img);

        const buttonCol = createElementWithClass('div', 'col-auto button');
        const playerLink = createElementWithClass('a', 'font-weight-medium');
        // Will probably do something else with this
        playerLink.href = `?p1=${player}`;
        playerLink.textContent = player;
        buttonCol.appendChild(playerLink);

        row.appendChild(imgCol);
        row.appendChild(buttonCol);

        const row2 = createElementWithClass('div', 'row');
        const col2 = createElementWithClass('div', 'col');
        const winsSpan = createElementWithClass('span', 'font-weight-bold');
        winsSpan.textContent = wins;
        col2.appendChild(winsSpan);
        row2.appendChild(col2);

        card.appendChild(row);
        card.appendChild(row2);
        col.appendChild(card);

        return col;
    };

    const player1Card = createPlayerCard(replay.p1, replay.p1icon, replay.p1wins);
    container.appendChild(player1Card);

    const footerCol = createElementWithClass('div', 'col-12 col-sm-6 col-md-2 text-center mb-3');
    const footerContainer = createElementWithClass('div', 'container');

    const downloadRow1 = createElementWithClass('div');
    const downloadButton1 = createElementWithClass('a', 'btn btn-outline-primary btn-sm btn-padding col-12 col-md-auto button text-light mb-1');
    downloadButton1.href = `/download?filename=${replay.filename}`;
    downloadButton1.textContent = 'Download Game';
    downloadRow1.appendChild(downloadButton1);

    const downloadRow2 = createElementWithClass('div');
    const downloadButton2 = createElementWithClass('a', 'btn btn-outline-primary btn-sm btn-padding col-12 col-md-auto button text-light mb-1');
    downloadButton2.href = `/download-set?filenames=${replay.set.join(',')}`;
    downloadButton2.textContent = 'Download Set';
    downloadRow2.appendChild(downloadButton2);

    const openRow = createElementWithClass('div');

    const toggleButton = createElementWithClass(
        'button',
        'btn btn-outline-primary btn-sm btn-padding col-12 col-md-auto button text-light mb-1'
    );

    const replayList = createElementWithClass(
        'div',
        'd-none'
     );

    toggleButton.type = 'button';
    toggleButton.textContent = `View Replays (${replay.set.length})`;

    replay.set.forEach((setReplay, index) => {
        const replayButton = createElementWithClass(
            'a',
            `btn btn-outline-secondary btn-sm btn-padding col-12 mb-1 button`

        );


        replayButton.href =
            `steam://run/586140/?load-replay=http://89.167.76.6:5000/download/${setReplay}`;

        replayButton.textContent = `Replay ${index + 1}`;

        replayList.appendChild(replayButton);
     });

    toggleButton.addEventListener('click', () => {
        const isHidden = replayList.classList.toggle('d-none');

        toggleButton.textContent = isHidden
            ? `View Replays (${replay.set.length})`
            : 'Hide Replays';

        toggleButton.setAttribute('aria-expanded', String(!isHidden));
    });

    openRow.appendChild(toggleButton);
    footerContainer.appendChild(openRow);
    footerContainer.appendChild(replayList);

    const dateRow = createElementWithClass('div');
    const dateCol = createElementWithClass('div');
    const dateSpan = createElementWithClass('span', 'main-font caption');
    const utcDateString = replay.datetime_;
    // Create a Date object using the UTC date string
    const date = new Date(utcDateString);
    const options = {
      weekday: 'short',
      year: 'numeric',
      month: 'long',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    };
    dateSpan.textContent = date.toLocaleString(undefined, options);

    dateCol.appendChild(dateSpan);
    dateRow.appendChild(dateCol);

    footerContainer.appendChild(downloadRow1);
    footerContainer.appendChild(downloadRow2);
    footerContainer.appendChild(openRow);
    footerContainer.appendChild(replayList);
    footerContainer.appendChild(dateRow);

    footerCol.appendChild(footerContainer);
    container.appendChild(footerCol);

    const player2Card = createPlayerCard(replay.p2, replay.p2icon, replay.p2wins);
    container.appendChild(player2Card);

    if (replay.p1wins > replay.p2wins) {
        player1Card.querySelector('.card').style.backgroundColor = amber;
        player2Card.querySelector('.card').style.backgroundColor = dusty;
    } else if (replay.p2wins > replay.p1wins) {
        player1Card.querySelector('.card').style.backgroundColor = dusty;
        player2Card.querySelector('.card').style.backgroundColor = amber;
    } else {
        player1Card.querySelector('.card').style.backgroundColor = granite;
        player2Card.querySelector('.card').style.backgroundColor = granite;
    }

    return container;
    },
};

export default replayLoader;


$(window).on('scroll', function() {

    if ($(window).scrollTop() + $(window).height() >= $(document).height() - 100) {
        replayLoader.loadReplays();
    }
});
