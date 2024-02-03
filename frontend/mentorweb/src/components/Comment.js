import React, { useState, useContext, useEffect } from 'react';
import { UserContext } from '../context/UserContext';
import { getCookie } from '../utils/GetCookie';

export default function Comment({ appointmentId }) {
    const { user } = useContext(UserContext);
    const [comment, setComment] = useState('');
    const [comments, setComments] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleInputChange = (e) => {
        setComment(e.target.value);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const csrfToken = getCookie('csrf_access_token');
        const payload = { "appointment_comment": comment };
        try {
            const response = await fetch(`/${user.account_type}/appointments/${appointmentId}/comment`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken,
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                alert('Comment posted!');
                fetchComments(); // Fetch comments again to update the list
            } else {
                const errorText = await response.text();
                alert('Error posting comment: ' + errorText);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    };

    const fetchComments = async () => {
        const csrfToken = getCookie('csrf_access_token');
        setIsLoading(true);
        try {
            const response = await fetch(`/${user.account_type}/appointments/${appointmentId}/comment`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken,
                },
            });
            if (response.ok) {
                const data = await response.json();
                setComments(data.comments);
            } else {
                const errorText = await response.text();
                setError('Error fetching comments: ' + errorText);
            }
        } catch (error) {
            console.error('Error:', error);
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchComments();
    }, [appointmentId, user.account_type]);

    const handleDelete = async (id) => {
        const csrfToken = getCookie('csrf_access_token');
        try {
            // Replace this URL with the URL for your server's delete comment endpoint
            await fetch(`/${user.account_type}/appointments/${appointmentId}/comment/${id}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken,
                },
            });
            setComments(comments.filter(comment => comment.id !== id));
        } catch (err) {
            console.error('Failed to delete comment:', err);
        }
    };

    return (
        <div className="flex flex-col mt-5">
            <h1 className='text-2xl font-bold'>Comments</h1>
            <form className="flex" onSubmit={handleSubmit}>
                <input className="border border-light-gray p-2 w-full"
                    type="text"
                    name="comment"
                    value={comment}
                    onChange={handleInputChange}
                    placeholder="Add a comment..."
                />
                <button className="bg-purple text-white p-2 ml-2 rounded-md" type="submit">Post</button>
            </form>
            <div id="comments-container">
                {isLoading ? (
                    <p>Loading comments...</p>
                ) : error ? (
                    <p>{error}</p>
                ) : (
                    comments.map((comment, index) => (
                        <div key={index} className="flex flex-col border border-light-gray p-2 mt-2">
                            <div className="flex justify-between">
                                <p className="font-bold">{comment.name}</p>
                                <div>
                                    <p className="text-xs">{new Date(comment.created_at).toLocaleString()}</p>
                                    <button onClick={() => handleDelete(comment.id)}>X</button>
                                </div>
                            </div>
                            <p>{comment.appointment_comment}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}