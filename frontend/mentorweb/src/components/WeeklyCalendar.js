/* WeeklyCalendar.js
 * Last Edited: 3/24/24
 *
 * Sets the general weekdays time blocks used
 * to populate the ProgramTimes table
 *
 * Known bugs:
 * -
 *
 */

import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { SingleInputTimeRangeField } from "@mui/x-date-pickers-pro/SingleInputTimeRangeField";

export default function WeeklyCalendar({
  functions,
  times,
  loadPage,
  program_id,
}) {
  // temp time range used for each SingleInputTimeRangeField
  const [timeRange, setTimeRange] = useState(["12:00", "12:30"]);

  // Store times for each weekday
  const [localTimes, setLocalTimes] = useState({
    Monday: [],
    Tuesday: [],
    Wednesday: [],
    Thursday: [],
    Friday: [],
  });

  // Show SingleInputTimeRangeField UI
  const [showTimeEntryField, setShowTimeEntryField] = useState({
    Monday: false,
    Tuesday: false,
    Wednesday: false,
    Thursday: false,
    Friday: false,
  });

  ////////////////////////////////////////////////////////
  //                 Handler Functions                  //
  ////////////////////////////////////////////////////////

  // handle onClick for each weekday header
  const handleWeekdayClick = (day) => {
    // detect remove click
    if (showTimeEntryField[day]) {
      handleRemoveLocalTime(day);
    }

    // flip boolean state for the weekday in timePickersList
    setShowTimeEntryField((prevState) => ({
      ...prevState,
      [day]: !prevState[day],
    }));
  };

  // edit timeRange onChange for SingleInputTimeRangeField
  const handleInputChange = (event, day) => {
    // format to military time
    const militaryTimeTimeRange = [
      event[0] && event[0].format("HH:mm"),
      event[1] && event[1].format("HH:mm"),
    ];

    // set temp time range variable
    setTimeRange(militaryTimeTimeRange);

    const convertedTimeRangeObj = { start_time: event[0], end_time: event[1] };

    setLocalTimes({ ...localTimes, [day]: convertedTimeRangeObj });
  };

  // remove time block that user allotted
  const handleRemoveLocalTime = (day) => {
    // clear times for day
    setLocalTimes((prevState) => ({
      ...prevState,
      [day]: [],
    }));

    // push changes to parent object
    functions.timesChangeFunction({
      type: program_id,
      name: day,
      value: [],
    });
  };

  // create button to push time block to parent function
  const handleCreateTimeBlock = (day, newTimeBlock) => {
    if (isValidTimeBlock(newTimeBlock)) {
      setLocalTimes({ ...localTimes, [day]: newTimeBlock });
      functions.timesChangeFunction({
        type: program_id,
        name: day,
        value: newTimeBlock,
      });
    } else {
      alert("Invalid time block entered.");
    }
  };

  // handleCreateChange helper: check if time block chosen is a valid range
  const isValidTimeBlock = (timeBlock) => {
    return timeBlock[0] < timeBlock[1];
  };

  ////////////////////////////////////////////////////////
  //               UseEffect Functions                  //
  ////////////////////////////////////////////////////////

  useEffect(() => {
    // load the weekday values on page load
    if (loadPage) {
      // set the headers based on incoming data
      const updatedShowTimeEntries = {};
      for (const day in times) {
        if (times.hasOwnProperty(day)) {
          updatedShowTimeEntries[day] = true;
        }
      }

      // show time fields
      setShowTimeEntryField((prevState) => ({
        ...prevState,
        ...Object.keys(updatedShowTimeEntries).reduce((acc, key) => {
          if (updatedShowTimeEntries[key]) {
            acc[key] = true;
          }
          return acc;
        }, {}),
      }));

      // set the times
      const updatedLocalTimes = {
        Monday: [],
        Tuesday: [],
        Wednesday: [],
        Thursday: [],
        Friday: [],
      };

      for (const day in times) {
        if (times.hasOwnProperty(day)) {
          // append random date to satisfy x-date-pickers library
          const start = dayjs(`2022-04-17T${times[day].start_time}`);
          const end = dayjs(`2022-04-17T${times[day].end_time}`);
          updatedLocalTimes[day] = { start_time: start, end_time: end };
        }
      }
      setLocalTimes(updatedLocalTimes);

      functions.loadPageFunction(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showTimeEntryField, times, localTimes, loadPage]);

  useEffect(() => {
    const anyDayHasData = Object.values(localTimes).some(
      (dayData) => dayData.length > 0 || Object.keys(dayData).length > 0
    );

    // Call param.showDuration based on the condition
    functions.setShowDuration(anyDayHasData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localTimes]);

  ////////////////////////////////////////////////////////
  //                 Render Functions                   //
  ////////////////////////////////////////////////////////

  // render the weekday labels with object creation onClick
  const renderWeekdayHeader = (day) => {
    return (
      <th
        className={`border-r w-1/5 hover:cursor-pointer ${
          showTimeEntryField[day] ? "bg-light-gray" : "bg-white"
        }`}
        name={day}
        onClick={() => handleWeekdayClick(day)}
      >
        {day}
      </th>
    );
  };

  // render the SingleInputTimeRangeField UI for each weekday
  const renderWeekdayBody = (day) => {
    return (
      <td>
        {showTimeEntryField[day] && (
          <div className={`flex flex-col items-center`}>
            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <SingleInputTimeRangeField
                label="Set Time"
                value={[localTimes[day].start_time, localTimes[day].end_time]}
                onChange={(e) => handleInputChange(e, day)}
                onBlur={() => handleCreateTimeBlock(day, timeRange)}
              />
            </LocalizationProvider>
          </div>
        )}
      </td>
    );
  };

  // HTML for webpage
  return (
    <div>
      <div className="font-bold text-2xl mb-4">
        <label className="whitespace-nowrap">Set Program Times:</label>
      </div>

      <div>
        <table className="w-full">
          <thead className="border">
            <tr>
              {renderWeekdayHeader("Monday")}
              {renderWeekdayHeader("Tuesday")}
              {renderWeekdayHeader("Wednesday")}
              {renderWeekdayHeader("Thursday")}
              {renderWeekdayHeader("Friday")}
            </tr>
          </thead>

          <br />

          <tbody>
            {renderWeekdayBody("Monday")}
            {renderWeekdayBody("Tuesday")}
            {renderWeekdayBody("Wednesday")}
            {renderWeekdayBody("Thursday")}
            {renderWeekdayBody("Friday")}
          </tbody>
        </table>
      </div>
    </div>
  );
}
