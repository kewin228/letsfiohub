import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

const API_URL = 'https://letsfiohub-1.onrender.com/api';

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState('Apex');
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  // Проверка авторизации
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const res = await fetch(API_URL + '/auth/me', {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            const data = await res.json();
            setUser(data);
          } else {
            localStorage.removeItem('token');
          }
        } catch (err) {
          console.error('Auth error:', err);
          localStorage.removeItem('token');
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  // Загрузка видео
  useEffect(() => {
    const loadVideos = async () => {
      try {
        const res = await fetch(API_URL + '/videos/?style=' + selectedStyle);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setVideos(data);
          } else {
            setVideos([]);
          }
        } else {
          setVideos([]);
        }
      } catch (err) {
        console.error('Video load error:', err);
        setVideos([]);
      }
    };
    
    loadVideos();
  }, [selectedStyle]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    router.reload();
  };

  const styles = ['Default', 'Cyberpunk', 'Cod', 'Fortnite', 'Minecraft', 'Valorant', 'Lol', 'Darksouls', 'Apex'];

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0F0F0F', color: 'white', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        Загрузка...
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0F0F0F', color: 'white' }}>
      <Head><title>LetsFioHub</title></Head>
      
      {/* Шапка */}
      <header style={{ padding: '20px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ color: '#FF6B00', margin: 0, cursor: 'pointer' }} onClick={() => router.push('/')}>
           LetsFioHub
        </h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          {user ? (
            <>
              <span style={{ padding: '8px 16px', color: '#FF6B00' }}>Привет, {user.display_name || user.username}!</span>
              <button onClick={handleLogout} style={{ padding: '8px 16px', background: '#333', color: 'white', border: '1px solid #FF6B00', borderRadius: '8px', cursor: 'pointer' }}>
                Выйти
              </button>
            </>
          ) : (
            <>
              <button onClick={() => router.push('/login')} style={{ padding: '8px 16px', background: 'transparent', color: 'white', border: '1px solid #FF6B00', borderRadius: '8px', cursor: 'pointer' }}>
                Войти
              </button>
              <button onClick={() => router.push('/register')} style={{ padding: '8px 16px', background: '#FF6B00', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
                Регистрация
              </button>
            </>
          )}
        </div>
      </header>

      <main style={{ padding: '40px 20px' }}>
        {/* Геймерские стили */}
        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ marginBottom: '15px' }}>🎮 Геймерские стили:</h3>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {styles.map((style) => (
              <button
                key={style}
                onClick={() => setSelectedStyle(style)}
                style={{
                  padding: '8px 16px',
                  background: selectedStyle === style ? '#FF6B00' : '#333',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.3s'
                }}
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        {/* Видео */}
        <div>
          <h2>Рекомендовано для вас</h2>
          {videos.length === 0 ? (
            <p style={{ color: '#666', marginTop: '20px' }}>Нет доступных видео</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px', marginTop: '20px' }}>
              {videos.map((video) => (
                <div key={video.id} style={{ background: '#1a1a1a', borderRadius: '10px', overflow: 'hidden', padding: '15px' }}>
                  {video.thumbnail && <img src={video.thumbnail} alt={video.title} style={{ width: '100%', borderRadius: '8px', marginBottom: '10px' }} />}
                  <h3 style={{ margin: '0 0 10px 0' }}>{video.title}</h3>
                  <p style={{ color: '#999', fontSize: '14px', margin: '0 0 10px 0' }}>{video.description}</p>
                  <a href={video.url} target="_blank" rel="noopener noreferrer" style={{ color: '#FF6B00', textDecoration: 'none' }}>
                    Смотреть →
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
