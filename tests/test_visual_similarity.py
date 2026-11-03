import io
from PIL import Image
from superchat.vision import VisualSearch


def photo():
    out = io.BytesIO()
    Image.new('RGB', (32,32), 'grey').save(out, format='PNG')
    return out.getvalue()


def test_similarity_ranks_real_ids_and_rejects_weak_matches(offline, monkeypatch):
    v = VisualSearch(offline)
    monkeypatch.setattr(v, 'classify', lambda _: {'accepted': True, 'label': 'laptop', 'confidence': .95, 'engine': 'test'})
    monkeypatch.setattr(v, 'features', lambda _: [[1., 0.]])
    monkeypatch.setattr(v, 'index_catalogue', lambda _: [('BM-1', [.7, .714]), ('BM-2', [.95,.312]), ('BM-3', [.3,.954]), ('BM-4', [1.,0.])])
    class Repo:
        def search(self, f):
            assert f == {'query': 'laptop'}
            return [{'id': f'BM-{i}'} for i in range(1,4)]
    prediction = v.search(photo(), Repo(), object())
    assert prediction['method'] == 'image_similarity'
    assert [m['id'] for m in prediction['matches']] == ['BM-2', 'BM-1']
    assert prediction['matches'][0]['score'] == .95


def test_uncertain_photo_does_not_search_catalogue(offline, monkeypatch):
    v = VisualSearch(offline)
    monkeypatch.setattr(v, 'classify', lambda _: {'accepted': False, 'label': 'other', 'confidence': .2, 'engine': 'test'})
    class Repo:
        def search(self, f):
            raise AssertionError('Uncertain images must not display arbitrary products')
    assert v.search(photo(), Repo(), object())['matches'] == []


def test_unavailable_encoder_has_explicit_category_fallback(offline, monkeypatch):
    v = VisualSearch(offline)
    monkeypatch.setattr(v, 'classify', lambda _: {'accepted': True, 'label': 'laptop', 'confidence': .9, 'engine': 'test'})
    def unavailable(_):
        raise ImportError()
    monkeypatch.setattr(v, 'features', unavailable)
    class Repo:
        def search(self, f):
            return [{'id':'BM-1'}]
    result = v.search(photo(), Repo(), object())
    assert result['method'] == 'category' and result['matches'] == [{'id':'BM-1', 'score':None}]


def test_earbud_photo_can_match_catalogue_headphones_by_image(offline, monkeypatch):
    v = VisualSearch(offline)
    monkeypatch.setattr(v, 'classify', lambda _: {'accepted': True, 'label': 'earbuds', 'confidence': .9, 'engine': 'test'})
    monkeypatch.setattr(v, 'features', lambda _: [[1., 0.]])
    monkeypatch.setattr(v, 'index_catalogue', lambda _: [('BM-wired', [1., 0.]), ('BM-buds', [.7, .714]), ('BM-unrelated', [1., 0.])])
    class Repo:
        def search(self, filters):
            return [{'id': 'BM-wired' if filters['query'] == 'headphones' else 'BM-buds'}]
    result = v.search(photo(), Repo(), object())
    assert [m['id'] for m in result['matches']] == ['BM-wired', 'BM-buds']
    assert result['matches'][0]['score'] == 1.
