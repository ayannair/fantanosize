import React, { useState } from 'react';
import './styles.css';
import axios from 'axios';
import LoadingIcon from './components/LoadingIcon';
import AlbumCard from './components/AlbumCard';
import CustomAlbumCard from './components/CustomAlbumCard';
import PercentileCard from './components/PercentileCard';

const App = () => {
  const [query, setQuery] = useState('');
  const [scores, setScores] = useState(null);
  const [customScores, setCustomScores] = useState(null);
  const [lyrics, setLyrics] = useState(null);
  const [selectedSong, setSelectedSong] = useState(null);
  const [topics, setTopics] = useState({});
  const [loading, setLoading] = useState(false);
  const [showTopics, setShowTopics] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showCustomCard, setShowCustomCard] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [customCardCreated, setCustomCardCreated] = useState(false); // Track if custom card has been created
  const [operationType, setOperationType] = useState(''); // Track the operation type ('create' or 'edit')
  const [percentiles, setPercentiles] = useState(null);
  const [showPercentileCard, setShowPercentileCard] = useState(false); // Track when to show the PercentileCard

  const handleInputChange = async (e) => {
    const value = e.target.value;
    setQuery(value);
  
    if (value.length > 1) {
      try {
        const response = await axios.get('https://albumace-93f2286af143.herokuapp.com/autocomplete', {
          params: { query: value }
        });
        setSuggestions(response.data);
      } catch (error) {
        console.error('Error fetching suggestions:', error);
      }
    } else {
      setSuggestions([]);
    }
  };
  
  const handleSearch = async () => {
    setScores(null);
    setLyrics(null);
    setSelectedSong(null);
    setTopics({});
    setLoading(true);
    setCustomScores(null);
    setShowCustomCard(false);
    setEditMode(false);
    setCustomCardCreated(false); // Reset custom card creation on new search
    setShowPercentileCard(false); // Reset the visibility of the PercentileCard on new search
  
    try {
      const response = await axios.get(`https://albumace-93f2286af143.herokuapp.com/search?query=${query}`);
      console.log(response.data);
  
      const { concept_score, features_score, lyrics_score, originality_score, overall_score, production_score, vocals_score } = response.data['score'];
      const lyricsData = response.data['lyrics'];
  
      setScores({ concept_score, features_score, lyrics_score, originality_score, overall_score, production_score, vocals_score });
      setLyrics(lyricsData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
      setSuggestions([]); // Clear suggestions after search
    }
  };
  

  const handleSongClick = async (songTitle) => {
    setShowTopics(false);

    try {
      const response = await axios.get('https://albumace-93f2286af143.herokuapp.com/get_topic', {
        params: { song_title: songTitle },
      });
      setTopics(prevTopics => ({ ...prevTopics, [songTitle]: response.data.topic }));
      setSelectedSong(songTitle);
    } catch (error) {
      console.error('Error fetching topic:', error);
    } finally {
      setLoading(false);
      setTimeout(() => setShowTopics(true), 500);
    }
  };

  const sortedLyrics = lyrics ? Object.entries(lyrics).sort(([aIndex], [bIndex]) => aIndex - bIndex) : [];

  const handleSaveScores = async (newScores) => {
    try {
      const response = await axios.post('https://albumace-93f2286af143.herokuapp.com/save_scores', {
        title: query,
        scores: newScores,
        operation_type: operationType, // Pass the operation type
      });
  
      console.log(response.data);
      if (response.data['updated_scores']) {
        const { concept_score, features_score, lyrics_score, originality_score, overall_score, production_score, vocals_score } = response.data['updated_scores'];
        setScores({ concept_score, features_score, lyrics_score, originality_score, overall_score, production_score, vocals_score });
      }
  
      if (response.data['percentiles']) {
        const { concept_score, features_score, lyrics_score, originality_score, overall_score, production_score, vocals_score } = response.data['percentiles'];
        setPercentiles({
          concept_score: Math.round(concept_score),
          features_score: Math.round(features_score),
          lyrics_score: Math.round(lyrics_score),
          originality_score: Math.round(originality_score),
          overall_score: Math.round(overall_score),
          production_score: Math.round(production_score),
          vocals_score: Math.round(vocals_score),
        });
        setShowPercentileCard(true); // Show the PercentileCard when scores are saved
      }
    } catch (error) {
      console.error('Error saving scores:', error);
    }
  
    setCustomScores(newScores);
    setEditMode(false);
    setShowCustomCard(false);
    setCustomCardCreated(true); // Mark custom card as created
  };

  const handleCreateCardClick = () => {
    setOperationType('create'); // Set operation type to 'create'
    setShowCustomCard(true);
    setEditMode(false);
  };

  const handleEditCardClick = () => {
    setOperationType('edit'); // Set operation type to 'edit'
    setEditMode(true);
  };

  return (
    <div className="container">
      <div className="header">
        <h1>AlbumAce</h1>
        <div className="search-bar">
          <input
            type="text"
            placeholder="[album name] by [artist name]"
            value={query}
            onChange={handleInputChange}
          />
          <button onClick={handleSearch}>Search</button>
          {suggestions.length > 0 && (
            <ul className="autocomplete-suggestions">
            {suggestions.map((suggestion, index) => (
              <li
                key={index}
                onClick={() => {
                  setQuery(suggestion);
                  setSuggestions([]); // Clear suggestions on click
                }}
              >
                {suggestion}
              </li>
            ))}
          </ul>
          )}
        </div>
      </div>
      {loading && <LoadingIcon loading={loading} />}
      <div className="bento-box">
        <div className="left-section">
          {lyrics && (
            <div className="lyrics-table">
              <h2>Songs</h2>
              <table>
                <tbody>
                  {sortedLyrics.map(([index, { title }]) => (
                    <tr key={index}>
                      <td>{title}</td>
                      <td>
                        <button
                          className="get-topics-button"
                          onClick={() => handleSongClick(title)}
                        >
                          {topics[title] ? 'View Topics' : 'Get Topics'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="right-section">
          {scores && <AlbumCard scores={scores} />}
          {selectedSong && topics[selectedSong] && (
            <div className={`topics-section ${showTopics ? 'fade-in' : 'fade-out'}`}>
              <h2>{selectedSong} is about...</h2>
              <ul>
                {topics[selectedSong].split('\n').map((topic, index) => (
                  <li key={index}>{topic}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
      <div className="custom-album-card-container">
  {scores && !loading && !customCardCreated && (
    <button onClick={handleCreateCardClick} className="edit-scores-button">
      Make Your Own Card!
    </button>
  )}

  {!loading && showCustomCard && (
    <CustomAlbumCard
      initialScores={customScores || scores}
      onSave={handleSaveScores}
    />
  )}

  {customScores && !editMode && customCardCreated && (
    <button onClick={handleEditCardClick} className="edit-scores-button">
      Edit Card
    </button>
  )}

  {editMode && (
    <CustomAlbumCard
      initialScores={customScores}
      onSave={handleSaveScores}
    />
  )}

  {/* Conditionally render the custom card and percentile card side by side */}
  {customScores && !editMode && (
    <div className="custom-and-percentile-container">
      <div className="custom-album-card-container">
        <AlbumCard scores={customScores} />
      </div>
      {showPercentileCard && percentiles && (
        <div className="percentile-card-container">
          <PercentileCard percentiles={percentiles} />
        </div>
      )}
    </div>
  )}
</div>
  </div>
);
};

export default App;
