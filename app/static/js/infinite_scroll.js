// Every request captures an immutable query snapshot and is accepted only while it is still the active generation
const replayLoader = {
    page: 1,
    hasNext: true,
    loading: false,
    replayString: null,
    activeRequest: null,
    generation: 0,
    lastError: null,

    _normalizeSearch(params) {
        // sorting so p1?=bob?p2=john and p2=john?p1=bob are treated as the same query
        const snapshot = this.cloneParams(params);
        snapshot.set('page', '1');
        snapshot.sort();
        return snapshot;
    },

    _queryKey(params) {
        const snapshot = this.cloneParams(params);
        snapshot.sort();
        return snapshot.toString();
    },

    _setLoading(value) {
        this.loading = value;
        if (value) {
            $('#loading').show();
        } else {
            $('#loading').hide();
        }
    },

    _isActive(request) {
        return this.activeRequest === request &&
            request.generation === this.generation &&
            request.queryKey === this._queryKey(this.replayString);
    },

    _historyState(data) {
        return {
            query: this.replayString.toString(),
            nextPage: this.page,
            hasNext: this.hasNext,
            replays: data.replays,
        };
    },
    // creating a copy of query params to ensure it's not mutated by other requests
    cloneParams(params) {
        return new URLSearchParams(params instanceof URLSearchParams ? params.toString() : params || '');
    },

    async startSearch(params = new URLSearchParams(window.location.search), { clear = true } = {}) {
        const querySnapshot = this._normalizeSearch(params);
        const previousRequest = this.activeRequest;

        this.generation += 1;
        const generation = this.generation;

        if (previousRequest) {
            previousRequest.controller.abort();
        }

        this.activeRequest = null;
        this.lastError = null;
        this.replayString = this.cloneParams(querySnapshot);
        this.page = 1
        this.hasNext = true
        this._setLoading(false)

        if (clear) {
            document.getElementById('replaysContainer')?.replaceChildren();
        }

        return this._requestPage(1, generation, querySnapshot);
    },

    async loadNextPage() {
        if (this.loading) {
            return { accepted: false, reason: 'loading' };
        }
        if (!this.hasNext) {
            return { accepted: false, reason: 'exhausted' };
        }

        if (!this.replayString) {
            return this.startSearch(new URLSearchParams(window.location.search));
        }

        return this._requestPage(this.page, this.generation, this.replayString);
    },

    async retry() {
        if (!this.lastError?.retryable) {
            return { accepted: false, reason: 'not-retryable' };
        }
        return this.loadNextPage();
    },

    async _requestPage(page, generation, baseQuery) {
        if (generation !== this.generation) {
            return { accepted: false, reason: 'stale-generation' };
        }

        const querySnapshot = this.cloneParams(baseQuery);
        querySnapshot.set('page', String(page));
        querySnapshot.sort();

        const controller = new AbortController();
        const request = {
            generation,
            queryString: querySnapshot.toString(),
            queryKey: this._queryKey(baseQuery),
            page,
            controller,
        };

        this.activeRequest = request;
        this.lastError = null;
        this._setLoading(true);

        try {
            const response = await fetch(`/api/replay-sets?${request.queryString}`, {
                signal: controller.signal,
            });

            if (!this._isActive(request)) {
                return { accepted: false, reason: 'stale' };
            }

            if (!response.ok) {
                if (response.status === 404) {
                    this.hasNext = false;
                    this.lastError = { status: 404, retryable: false };
                } else if (response.status === 429) {
                    this.lastError = { status: 429, retryable: true };
                } else {
                    this.lastError = { status: response.status, retryable: true };
                }
                return { accepted: false, status: response.status, retryable: this.lastError.retryable };
            }

            const data = await response.json();

            if (!this._isActive(request) || controller.signal.aborted) {
                return { accepted: false, reason: 'stale' };
            }

            for (const replay of data.replays) {
                $('#replaysContainer').append(this.renderReplay(replay));
            }

            this.hasNext = Boolean(data.has_next);
            // page state based on the accepted request’s snapshot
            this.page = request.page + 1
            this.lastError = null;

            return {
                accepted: true,
                data,
                historyState: this._historyState(data),
                query: this.replayString.toString(),
            };

        } catch (error) {
            if (!this._isActive(request)) {
                return { accepted: false, reason: 'stale' };
            }

            if (error.name === 'AbortError') {
                return { accepted: false, reason: 'aborted' };
            }

            this.lastError = { status: null, retryable: true, error };
            console.error('Error fetching replays', error);
            return { accepted: false, reason: 'network-error', retryable: true };
        } finally {

            if (this._isActive(request)) {
                this._setLoading(false);
                this.activeRequest = null;
            }
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

replayLoader.replayString = replayLoader.cloneParams(replayLoader._normalizeSearch(window.location.search));
replayLoader.page = 1;

export default replayLoader;


$(window).on('scroll', function() {

    if ($(window).scrollTop() + $(window).height() >= $(document).height() - 100) {
        replayLoader.loadNextPage();
    }
});
