// Import Axios for making HTTP requests to the backend API
import axios from "axios";

// Send a request to create a new user with the given username
export async function createUser(username) {
  // POST to the brainzOS /api/user/create endpoint with username payload
  const res = await axios.post("/api/user/create", { username });

  // Return the response data (e.g., { username, api_key })
  return res.data;
}
