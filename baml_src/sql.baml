// Defining a data model.
class SQLQuery {
  query string
}

// Create a function to extract the resume from a string.
function GenerateSQLQuery(user_query: string, schema: string, engine: string) -> SQLQuery {
  client "google-ai/gemini-2.5-flash"
  prompt #"
    Given an input question, create a syntactically correct SQL query for the {{ engine }} engine
    to run to help find the answer. You can order the results by a relevant column to
    return the most interesting examples in the database.

    Pay attention to use only the column names that you can see in the schema description.
    Be careful to not query for columns that do not exist. Also, pay attention to which column
    is in which table.

    Refer to the following schema to build the query:
    {{ schema }}

    An example of a record:
    3|50|MALE|Subscription|asdfqwerty@email.com|12345678

    Input question:
    {{ user_query }}

    {{ ctx.output_format }}
  "#
}

test SQLQuery {
  functions [GenerateSQLQuery]
  args {
    schema #"
      Table: "purchases"
      0|customer_id|INTEGER|1||1
      1|age|INTEGER|0||0
      2|gender|VARCHAR(6)|0||0
      3|type|VARCHAR|0||0
      4|email|VARCHAR|0||0
      5|phone_number|VARCHAR(14)|0||0
    "#
    user_query "How many customers are 18 years or older and female?"
    engine "MySQL"
  }
}
