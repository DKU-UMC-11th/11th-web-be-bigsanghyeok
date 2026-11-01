// This page and API run on different origins: requests go directly to Spring, without a proxy.
const api = new URLSearchParams(location.search).get('api') || 'http://localhost:8080';
const $ = id => document.getElementById(id);

async function request(kind, path, button, render) {
  button.disabled = true;
  const feedback = $(`${kind}-feedback`);
  feedback.textContent = '확인하고 있어요…';
  feedback.className = 'feedback';
  $(`${kind}-status`).textContent = '요청 중';
  $(`${kind}-json`).textContent = '';
  if (kind === 'ratings') $('ratings-list').replaceChildren();
  try {
    const response = await fetch(api + path);
    const data = await response.json();
    $(`${kind}-status`).textContent = `${response.status} ${response.statusText}`;
    $(`${kind}-json`).textContent = JSON.stringify(data, null, 2);
    if (!response.ok) throw new Error(response.status === 404 ? '존재하지 않는 회원입니다.' : '요청 내용을 확인해 주세요.');
    render(data, feedback);
  } catch (error) {
    feedback.className = 'feedback error';
    feedback.textContent = error instanceof TypeError ? '서버에 연결할 수 없습니다. 서버 주소와 CORS 설정을 확인해 주세요.' : error.message;
    if (error instanceof TypeError) {
      $(`${kind}-status`).textContent = '연결 오류';
      $(`${kind}-json`).textContent = error.message;
    }
    console.error(error);
  } finally { button.disabled = false; }
}

for (const kind of ['nickname', 'email']) {
  $(`${kind}-form`).addEventListener('submit', event => {
    event.preventDefault();
    request(kind, `/members/${kind}/${encodeURIComponent($(kind).value)}`, event.submitter, (data, feedback) => {
      feedback.className = `feedback ${data.available ? 'ok' : 'error'}`;
      feedback.textContent = data.available ? '사용할 수 있습니다.' : '이미 사용 중입니다.';
    });
  });
}

$('ratings-form').addEventListener('submit', event => {
  event.preventDefault();
  request('ratings', `/members/${encodeURIComponent($('member-id').value)}/ratings`, event.submitter, (ratings, feedback) => {
    feedback.className = 'feedback ok';
    feedback.textContent = ratings.length ? `총 ${ratings.length}개의 영화 기록 · 최신 등록순` : '아직 남긴 평점이 없습니다.';
    $('ratings-list').replaceChildren(...ratings.map(rating => {
      const card = document.createElement('article');
      card.className = 'rating-card';
      const icon = document.createElement('span'); icon.className = 'movie-icon'; icon.textContent = '▶';
      const content = document.createElement('div');
      const title = document.createElement('h3'); title.textContent = `영화 #${rating.movieId}`;
      const stars = document.createElement('span'); stars.className = 'stars'; stars.textContent = `${'★'.repeat(rating.score)}${'☆'.repeat(5-rating.score)} ${rating.score}/5`;
      const comment = document.createElement('p'); comment.textContent = rating.comment || '코멘트 없이 별점을 남겼어요.';
      content.append(title, stars, comment); card.append(icon, content); return card;
    }));
  });
});
