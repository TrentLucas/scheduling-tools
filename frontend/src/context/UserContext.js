/* UserContext.js
 * Last Edited: 3/26/24
 *
 * Allows to pass down user data to a component without having
 * to pass props through every level in the component tree of Canvas Meeting Scheduler.
 *
 * Known bugs:
 * -
 *
 */

import React, { createContext, useState } from "react";

// Context Variables
export const UserContext = createContext(null);

export const UserProvider = ({ children }) => {
  // User Data Variables
  const [user, setUser] = useState(null);

  ////////////////////////////////////////////////////////
  //                 Render Functions                   //
  ////////////////////////////////////////////////////////

  // HTML for webpage
  return (
    // Provide Child components with access to values user and setUser and their data
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
};
